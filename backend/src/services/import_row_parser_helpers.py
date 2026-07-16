from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from src.models import FeeType
from src.schemas.fee import FeeCreate
from src.services.import_formula import resolve_numeric_value
from src.services.import_parsers import (
    get_date_format,
    get_mapped_col,
    parse_datetime_safe,
    parse_decimal_safe,
)


def resolve_enum_mapping(
    schema_mappings: dict,
    category: str,
    raw_val: str | None,
    default: str | None = None,
) -> str | None:
    # ponytail: Consolidated redundant enum mapping lookup logic to prevent duplication.
    if not raw_val:
        return default
    trimmed = raw_val.strip()
    mappings = schema_mappings.get("enum_mappings", {}).get(category, {})
    for key, val_list in mappings.items():
        if trimmed in val_list or trimmed == key:
            return key
    return default


def _group_suffixes(base: str, columns: dict[str, Any], schema_mappings: dict[str, Any]) -> list[str]:
    """Collect the mapped suffixes ('' plus '__N' variants) for a fee/tax field group.

    The wizard maps extra fee/tax groups as indexed db keys (fee_amount__2, ...).
    Formula-mapped groups have no `columns` entry, so formula keys count too.
    The regex is anchored: `fee_amount` must never match unrelated future keys.
    """
    pattern = re.compile(rf"^{re.escape(base)}(__\d+)$")
    keys = set(columns or {}) | set((schema_mappings or {}).get("formulas") or {})
    suffixes = {""}
    for key in keys:
        match = pattern.match(key)
        if match:
            suffixes.add(match.group(1))
    return sorted(suffixes, key=lambda s: int(s[2:]) if s else 0)


def _resolve_fee_group(
    row: dict[str, str],
    columns: dict[str, Any],
    transformations: dict[str, Any],
    schema_mappings: dict[str, Any],
    decimal_separator: str,
    op_type: str,
    csv_action: str,
    currency: str,
    base: str,
    suffix: str,
    default_type: str,
    fallback_enum: FeeType,
) -> FeeCreate | None:
    """Resolve one fee/tax group (base group when suffix == '') into a FeeCreate."""
    # resolve_numeric_value supports formula-mapped fee/tax fields with no column entry.
    val = resolve_numeric_value(
        f"{base}_amount{suffix}",
        row,
        columns=columns,
        schema_mappings=schema_mappings,
        transformations=transformations,
        decimal_separator=decimal_separator,
        op_type=op_type,
        csv_action=csv_action,
    )
    if not val or val <= 0:
        return None

    curr = row.get(get_mapped_col(columns, f"{base}_currency{suffix}", op_type, csv_action)) or currency
    # Categorization column: the group's own fee_type__N when mapped, else the shared fee_type.
    type_col = get_mapped_col(columns, f"fee_type{suffix}", op_type, csv_action) if suffix else None
    if not type_col:
        type_col = get_mapped_col(columns, "fee_type", op_type, csv_action)
    raw_type = row.get(type_col) if type_col else None
    resolved_type = None
    if suffix:
        resolved_type = resolve_enum_mapping(schema_mappings, f"fee_type{suffix}", raw_type)
    if not resolved_type:
        resolved_type = resolve_enum_mapping(schema_mappings, "fee_type", raw_type, default=default_type)
    try:
        type_enum = FeeType(resolved_type)
    except ValueError:
        type_enum = fallback_enum

    if base == "tax":
        notes = "Withholding tax"
    else:
        notes = "Currency conversion fee" if resolved_type == "conversion" else "Fee"

    return FeeCreate(amount=val, currency=curr, fee_type=type_enum, notes=notes)


def resolve_fees_and_taxes(
    row: dict[str, str],
    columns: dict[str, Any],
    transformations: dict[str, Any],
    schema_mappings: dict[str, Any],
    decimal_separator: str,
    op_type: str,
    csv_action: str,
    currency: str,
) -> list[FeeCreate]:
    """Parse and resolve FeeCreate child objects for the transaction row.

    Each mapped fee/tax group ('fee_amount', 'fee_amount__2', 'tax_amount', ...)
    yields at most one FeeCreate; the DB stores them as a list per transaction.
    """
    fees: list[FeeCreate] = []
    for base, default_type, fallback_enum in (
        ("fee", "conversion", FeeType.OTHER),
        ("tax", "withholding_tax", FeeType.WITHHOLDING_TAX),
    ):
        for suffix in _group_suffixes(f"{base}_amount", columns, schema_mappings):
            fee = _resolve_fee_group(
                row,
                columns,
                transformations,
                schema_mappings,
                decimal_separator,
                op_type,
                csv_action,
                currency,
                base,
                suffix,
                default_type,
                fallback_enum,
            )
            if fee:
                fees.append(fee)
    return fees


def resolve_merchant_and_ref_fields(
    row: dict[str, str],
    columns: dict[str, Any],
    op_type: str,
    csv_action: str,
    notes: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Parse merchant and reference values from mapping configuration."""
    merchant_name = row.get(get_mapped_col(columns, "merchant_name", op_type, csv_action))
    merchant_category = row.get(get_mapped_col(columns, "merchant_category", op_type, csv_action))

    source_ref_col = get_mapped_col(columns, "source_reference", op_type, csv_action)
    source_reference = row.get(source_ref_col) if source_ref_col else None
    dest_ref_col = get_mapped_col(columns, "destination_reference", op_type, csv_action)
    destination_reference = row.get(dest_ref_col) if dest_ref_col else None

    if op_type == "transfer_in" and not source_reference:
        source_reference = notes or "CSV Import"
    if op_type == "transfer_out" and not destination_reference:
        destination_reference = notes or "CSV Import"

    return merchant_name, merchant_category, source_reference, destination_reference


def resolve_trade_fields(  # noqa: C901, PLR0912
    row: dict[str, str],
    columns: dict[str, Any],
    schema_mappings: dict[str, Any],
    op_type: str,
    csv_action: str,
    trade_side: str | None,
    order_type_val: str | None,
    unit_price: Decimal | None,
    decimal_separator: str,
    date_formats: dict[str, Any],
) -> tuple[str | None, str | None, Decimal | None, Decimal | None, Decimal | None, str | None, Any, Any]:
    """Parse limit/stop/execution prices, statuses, sides, and dates for trades."""
    if op_type == "trade":
        if not trade_side:
            trade_side_col = get_mapped_col(columns, "trade_side", op_type, csv_action)
            raw_trade_side = row.get(trade_side_col) if trade_side_col else None
            trade_side = resolve_enum_mapping(schema_mappings, "trade_side", raw_trade_side, default="buy")

        if not order_type_val:
            order_type_col = get_mapped_col(columns, "order_type", op_type, csv_action)
            raw_order_type = row.get(order_type_col) if order_type_col else None
            order_type_val = resolve_enum_mapping(schema_mappings, "order_type", raw_order_type, default="market")

    def _numeric(db_key: str) -> Decimal | None:
        return resolve_numeric_value(
            db_key,
            row,
            columns=columns,
            schema_mappings=schema_mappings,
            transformations=schema_mappings.get("transformations", {}),
            decimal_separator=decimal_separator,
            op_type=op_type,
            csv_action=csv_action,
        )

    limit_price = None
    if op_type == "trade" and order_type_val in ("limit", "stop_limit"):
        limit_price = _numeric("limit_price")
        if limit_price is None:
            limit_price = unit_price

    stop_price = None
    if op_type == "trade" and order_type_val in ("stop", "stop_limit"):
        stop_price = _numeric("stop_price")

    execution_price = None
    if op_type == "trade":
        execution_price = _numeric("execution_price")

    order_status = None
    if op_type == "trade":
        os_col = get_mapped_col(columns, "order_status", op_type, csv_action)
        raw_order_status = row.get(os_col) if os_col else None
        order_status = resolve_enum_mapping(schema_mappings, "order_status", raw_order_status, default="filled")

    order_placed_at = None
    filled_at = None
    if op_type == "trade":
        op_col = get_mapped_col(columns, "order_placed_at", op_type, csv_action)
        if op_col:
            op_str = row.get(op_col)
            if op_str:
                op_fmt = get_date_format(date_formats, "order_placed_at", op_type, csv_action)
                order_placed_at = parse_datetime_safe(op_str, op_fmt)
        fa_col = get_mapped_col(columns, "filled_at", op_type, csv_action)
        if fa_col:
            fa_str = row.get(fa_col)
            if fa_str:
                fa_fmt = get_date_format(date_formats, "filled_at", op_type, csv_action)
                filled_at = parse_datetime_safe(fa_str, fa_fmt)

    return (
        trade_side,
        order_type_val,
        limit_price,
        stop_price,
        execution_price,
        order_status,
        order_placed_at,
        filled_at,
    )


def resolve_category_fields(
    row: dict[str, str],
    columns: dict[str, Any],
    schema_mappings: dict[str, Any],
    op_type: str,
    csv_action: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Parse categories for interest, expense, revenue, or payment methods."""
    interest_type = None
    if op_type == "interest":
        it_col = get_mapped_col(columns, "interest_type", op_type, csv_action)
        raw_it = row.get(it_col) if it_col else None
        interest_type = resolve_enum_mapping(schema_mappings, "interest_type", raw_it, default="cash_interest")

    expense_category = None
    revenue_category = None
    payment_method = None
    if op_type == "expense":
        ec_col = get_mapped_col(columns, "expense_category", op_type, csv_action)
        raw_ec = row.get(ec_col) if ec_col else None
        expense_category = resolve_enum_mapping(schema_mappings, "expense_category", raw_ec, default="other")
    elif op_type == "revenue":
        rc_col = get_mapped_col(columns, "revenue_category", op_type, csv_action)
        raw_rc = row.get(rc_col) if rc_col else None
        revenue_category = resolve_enum_mapping(schema_mappings, "revenue_category", raw_rc, default="other")

    if op_type in ("expense", "revenue"):
        pm_col = get_mapped_col(columns, "payment_method", op_type, csv_action)
        raw_pm = row.get(pm_col) if pm_col else None
        payment_method = resolve_enum_mapping(schema_mappings, "payment_method", raw_pm)

    return interest_type, expense_category, revenue_category, payment_method


def resolve_fx_rate_change_fields(  # noqa: C901
    row: dict[str, str],
    columns: dict[str, Any],
    decimal_separator: str,
    currency: str,
    op_type: str,
    csv_action: str,
    exchange_rate: Decimal | None,
    price_currency: str | None,
    notes: str | None,
) -> tuple[str | None, str | None, Decimal | None]:
    """Parse source and target currencies, resolving conversion ratios from FX operations."""
    source_currency = None
    target_currency = None

    if op_type == "fx_rate_change":
        if notes and " -> " in notes:
            try:
                parts = notes.split(" -> ")
                from_part = parts[0].strip().split()
                to_part = parts[1].strip().split()
                if len(from_part) == 2 and len(to_part) == 2:  # noqa: PLR2004
                    from_amt = parse_decimal_safe(from_part[0], decimal_separator)
                    from_curr = from_part[1].strip()
                    to_amt = parse_decimal_safe(to_part[0], decimal_separator)
                    to_curr = to_part[1].strip()
                    if from_amt and to_amt and from_amt > 0:
                        source_currency = from_curr
                        target_currency = to_curr
                        exchange_rate = to_amt / from_amt
            except Exception:  # noqa: BLE001, S110
                pass

        if not source_currency or not target_currency:
            source_currency = row.get(get_mapped_col(columns, "source_currency", op_type, csv_action))
            target_currency = row.get(get_mapped_col(columns, "target_currency", op_type, csv_action))
            if source_currency:
                source_currency = source_currency.strip()
            if target_currency:
                target_currency = target_currency.strip()
            if not exchange_rate:
                from_amt = parse_decimal_safe(
                    row.get(get_mapped_col(columns, "from_amount", op_type, csv_action)),
                    decimal_separator,
                )
                to_amt = parse_decimal_safe(
                    row.get(get_mapped_col(columns, "to_amount", op_type, csv_action)),
                    decimal_separator,
                )
                if from_amt and to_amt and from_amt > 0:
                    exchange_rate = to_amt / from_amt

        source_currency = source_currency or currency
        target_currency = target_currency or currency
        exchange_rate = exchange_rate or Decimal("1.0")
    elif price_currency and price_currency != currency:
        source_currency = currency
        target_currency = price_currency

    return source_currency, target_currency, exchange_rate
