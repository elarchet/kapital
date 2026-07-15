from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any

from src.services.import_formula import resolve_numeric_value
from src.services.import_parsers import (
    get_date_format,
    get_mapped_col,
    parse_datetime_safe,
    resolve_config_value,
)
from src.services.import_row_parser_helpers import (
    resolve_category_fields,
    resolve_enum_mapping,
    resolve_fees_and_taxes,
    resolve_fx_rate_change_fields,
    resolve_merchant_and_ref_fields,
    resolve_trade_fields,
)


def parse_csv_row(  # noqa: C901, PLR0912, PLR0915
    row: dict[str, str],
    columns: dict[str, Any],
    type_mappings: dict[str, Any],
    scaling: dict[str, Any],
    transformations: dict[str, Any],
    date_formats: dict[str, Any],
    schema_mappings: dict[str, Any],
    decimal_separator: str,
) -> dict[str, Any] | None:
    op_col = schema_mappings.get("operation_type_column") or columns.get("operation_type") or "Action"
    csv_action = row.get(op_col)
    if not csv_action:
        return None
    csv_action = csv_action.strip()

    # Resolve polymorphic operation type
    op_type = None
    op_mappings = schema_mappings.get("enum_mappings", {}).get("operation_type")
    if not op_mappings:
        op_mappings = type_mappings
    for key, val_list in op_mappings.items():
        if csv_action in val_list:
            op_type = key
            break

    if not op_type:
        return None

    trade_side = None
    order_type_val = None
    if op_type in ("buy", "sell", "limit_buy", "limit_sell"):
        trade_side = "buy" if op_type in ("buy", "limit_buy") else "sell"
        order_type_val = "limit" if op_type in ("limit_buy", "limit_sell") else "market"
        op_type = "trade"

    # Extract values
    ticker = row.get(get_mapped_col(columns, "ticker", op_type, csv_action))
    isin = row.get(get_mapped_col(columns, "isin", op_type, csv_action))

    name_col = get_mapped_col(columns, "name", op_type, csv_action)
    raw_name = row.get(name_col) if name_col else None
    name_was_set = bool(raw_name and raw_name.strip())
    name = raw_name.strip() if name_was_set else (ticker or isin or "Asset")

    notes = row.get(get_mapped_col(columns, "notes", op_type, csv_action))

    # Transaction ID resolution with custom options
    transaction_id_col = get_mapped_col(columns, "transaction_id", op_type, csv_action)
    raw_transaction_id = row.get(transaction_id_col) if transaction_id_col else None

    # User-selected subset of columns feeding both the auto ID and the dedup key.
    hash_cols = resolve_config_value(schema_mappings.get("hash_columns"), None, op_type, csv_action)
    hash_row = {k: v for k, v in row.items() if k in hash_cols} if hash_cols else dict(row)

    # Read the enrichment option
    enrich_opt = schema_mappings.get("enrich_transaction_ids")
    if enrich_opt is None:
        # Fallback to legacy boolean
        legacy = schema_mappings.get("generate_auto_ids")
        enrich_opt = "when_empty" if legacy is not False else "never"

    # ponytail: Delegated config lookup to resolve_config_value helper
    opt = resolve_config_value(enrich_opt, None, op_type, csv_action, default="when_empty")

    has_raw = bool(raw_transaction_id and raw_transaction_id.strip())

    # No transaction_id column required: some brokers (e.g. Fortuneo) have none at all.
    should_generate = opt == "always" or (opt == "when_empty" and not has_raw)

    if should_generate:
        serialized = ",".join(f"{k}:{v}" for k, v in sorted(hash_row.items()) if v is not None)
        row_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        transaction_id = f"auto-{row_hash}"
    elif has_raw:
        transaction_id = raw_transaction_id.strip()
    else:
        transaction_id = None

    currency = row.get(get_mapped_col(columns, "currency", op_type, csv_action)) or "EUR"

    executed_at_str = row.get(get_mapped_col(columns, "executed_at", op_type, csv_action))
    if not executed_at_str:
        return None
    date_fmt = get_date_format(date_formats, "executed_at", op_type, csv_action)
    executed_at = parse_datetime_safe(executed_at_str, date_fmt)

    def _numeric(db_key: str) -> Decimal | None:
        return resolve_numeric_value(
            db_key,
            row,
            columns=columns,
            schema_mappings=schema_mappings,
            transformations=transformations,
            decimal_separator=decimal_separator,
            op_type=op_type,
            csv_action=csv_action,
        )

    quantity = _numeric("quantity")
    unit_price = _numeric("unit_price")
    total_amount = _numeric("total_amount")
    if total_amount is None:
        total_amount = Decimal(0)

    # Apply scaling based on currency
    price_currency = row.get(get_mapped_col(columns, "price_currency", op_type, csv_action)) or currency
    if price_currency in scaling.get("unit_price", {}):
        factor = Decimal(str(scaling["unit_price"][price_currency]))
        if unit_price:
            unit_price *= factor
        if price_currency == "GBX":
            price_currency = "GBP"
    if currency in scaling.get("total_amount", {}):
        factor = Decimal(str(scaling["total_amount"][currency]))
        total_amount *= factor
        if currency == "GBX":
            currency = "GBP"

    exchange_rate = _numeric("exchange_rate")

    # Call external helper for fees and taxes
    fees = resolve_fees_and_taxes(
        row=row,
        columns=columns,
        transformations=transformations,
        schema_mappings=schema_mappings,
        decimal_separator=decimal_separator,
        op_type=op_type,
        csv_action=csv_action,
        currency=currency,
    )

    # Call external helper for merchant and reference fields
    merchant_name, merchant_category, source_reference, destination_reference = resolve_merchant_and_ref_fields(
        row=row,
        columns=columns,
        op_type=op_type,
        csv_action=csv_action,
        notes=notes,
    )

    dividend_per_share = unit_price if op_type == "dividend" else None
    if op_type == "dividend" and dividend_per_share is None:
        dividend_per_share = Decimal("0.0")

    # Call external helper for trades
    (
        trade_side,
        order_type_val,
        limit_price,
        stop_price,
        execution_price,
        order_status,
        order_placed_at,
        filled_at,
    ) = resolve_trade_fields(
        row=row,
        columns=columns,
        schema_mappings=schema_mappings,
        op_type=op_type,
        csv_action=csv_action,
        trade_side=trade_side,
        order_type_val=order_type_val,
        unit_price=unit_price,
        decimal_separator=decimal_separator,
        date_formats=date_formats,
    )

    # Call external helper for interest, expense, revenue categories
    interest_type, expense_category, revenue_category, payment_method = resolve_category_fields(
        row=row,
        columns=columns,
        schema_mappings=schema_mappings,
        op_type=op_type,
        csv_action=csv_action,
    )

    fee_category = notes or "other" if op_type == "fee" else None
    tax_category = notes or "withholding" if op_type == "tax" else None

    # Call external helper for FX rate changes
    source_currency, target_currency, exchange_rate = resolve_fx_rate_change_fields(
        row=row,
        columns=columns,
        decimal_separator=decimal_separator,
        currency=currency,
        op_type=op_type,
        csv_action=csv_action,
        exchange_rate=exchange_rate,
        price_currency=price_currency,
        notes=notes,
    )

    # Extract split_sub_type for stock splits (schema-driven close/open/combined)
    split_sub_type: str | None = None
    if op_type == "stock_split":
        split_sub_type_col = get_mapped_col(columns, "split_sub_type", op_type, csv_action)
        raw_sub_type = row.get(split_sub_type_col) if split_sub_type_col else None
        split_sub_type = resolve_enum_mapping(schema_mappings, "split_sub_type", raw_sub_type, default=None)

    return {
        "op_type": op_type,
        "ticker": ticker,
        "isin": isin,
        "name": name,
        "name_was_set": name_was_set,
        "quantity": quantity,
        "unit_price": unit_price,
        "price_currency": price_currency,
        "total_amount": total_amount,
        "currency": currency,
        "executed_at": executed_at,
        "notes": notes,
        "transaction_id": transaction_id,
        "native_transaction_id": raw_transaction_id.strip() if has_raw else None,
        "_raw_row": dict(row),
        "_hash_row": hash_row,
        "exchange_rate": exchange_rate,
        "fees": fees,
        "merchant_name": merchant_name,
        "merchant_category": merchant_category,
        "source_reference": source_reference,
        "destination_reference": destination_reference,
        "dividend_per_share": dividend_per_share,
        "limit_price": limit_price,
        "fee_category": fee_category,
        "tax_category": tax_category,
        "source_currency": source_currency,
        "target_currency": target_currency,
        "csv_action": csv_action,
        "trade_side": trade_side,
        "order_type": order_type_val,
        "order_status": order_status,
        "stop_price": stop_price,
        "execution_price": execution_price,
        "order_placed_at": order_placed_at,
        "filled_at": filled_at,
        "expense_category": expense_category,
        "revenue_category": revenue_category,
        "payment_method": payment_method,
        "interest_type": interest_type,
        "split_sub_type": split_sub_type,
    }
