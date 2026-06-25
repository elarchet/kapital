from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.models import FeeType
from src.schemas.fee import FeeCreate
from src.services.import_parsers import (
    apply_transformation,
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
    """Parse and resolve FeeCreate child objects for the transaction row."""
    fees = []
    fee_amt_col = get_mapped_col(columns, "fee_amount", op_type, csv_action)
    if fee_amt_col:
        fee_val = parse_decimal_safe(row.get(fee_amt_col), decimal_separator)
        fee_val = apply_transformation(transformations, "fee_amount", fee_val, op_type, csv_action)
        if fee_val and fee_val > 0:
            fee_curr = row.get(get_mapped_col(columns, "fee_currency", op_type, csv_action)) or currency
            fee_type_col = get_mapped_col(columns, "fee_type", op_type, csv_action)
            raw_fee_type = row.get(fee_type_col) if fee_type_col else None
            resolved_fee_type = resolve_enum_mapping(schema_mappings, "fee_type", raw_fee_type, default="conversion")
            try:
                fee_type_enum = FeeType(resolved_fee_type)
            except ValueError:
                fee_type_enum = FeeType.OTHER

            fees.append(
                FeeCreate(
                    amount=fee_val,
                    currency=fee_curr,
                    fee_type=fee_type_enum,
                    notes="Currency conversion fee" if resolved_fee_type == "conversion" else "Fee",
                ),
            )

    tax_amt_col = get_mapped_col(columns, "tax_amount", op_type, csv_action)
    if tax_amt_col:
        tax_val = parse_decimal_safe(row.get(tax_amt_col), decimal_separator)
        tax_val = apply_transformation(transformations, "tax_amount", tax_val, op_type, csv_action)
        if tax_val and tax_val > 0:
            tax_curr = row.get(get_mapped_col(columns, "tax_currency", op_type, csv_action)) or currency
            fee_type_col = get_mapped_col(columns, "fee_type", op_type, csv_action)
            raw_fee_type = row.get(fee_type_col) if fee_type_col else None
            resolved_tax_type = resolve_enum_mapping(
                schema_mappings,
                "fee_type",
                raw_fee_type,
                default="withholding_tax",
            )
            try:
                tax_type_enum = FeeType(resolved_tax_type)
            except ValueError:
                tax_type_enum = FeeType.WITHHOLDING_TAX

            fees.append(
                FeeCreate(
                    amount=tax_val,
                    currency=tax_curr,
                    fee_type=tax_type_enum,
                    notes="Withholding tax",
                ),
            )

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

    limit_price = None
    if op_type == "trade" and order_type_val in ("limit", "stop_limit"):
        lp_col = get_mapped_col(columns, "limit_price", op_type, csv_action)
        limit_price = parse_decimal_safe(row.get(lp_col), decimal_separator) if lp_col else None
        if limit_price is None:
            limit_price = unit_price

    stop_price = None
    if op_type == "trade" and order_type_val in ("stop", "stop_limit"):
        sp_col = get_mapped_col(columns, "stop_price", op_type, csv_action)
        stop_price = parse_decimal_safe(row.get(sp_col), decimal_separator) if sp_col else None

    execution_price = None
    if op_type == "trade":
        ep_col = get_mapped_col(columns, "execution_price", op_type, csv_action)
        execution_price = parse_decimal_safe(row.get(ep_col), decimal_separator) if ep_col else None

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
