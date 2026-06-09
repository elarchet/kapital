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
    csv_action = row.get(columns.get("operation_type", "Action"))
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
    name = row.get(get_mapped_col(columns, "name", op_type, csv_action)) or ticker or isin or "Asset"
    notes = row.get(get_mapped_col(columns, "notes", op_type, csv_action))
    transaction_id = row.get(get_mapped_col(columns, "transaction_id", op_type, csv_action))
    currency = row.get(get_mapped_col(columns, "currency", op_type, csv_action)) or "EUR"

    executed_at_str = row.get(get_mapped_col(columns, "executed_at", op_type, csv_action))
    if not executed_at_str:
        return None
    date_fmt = get_date_format(date_formats, "executed_at", op_type, csv_action)
    executed_at = parse_datetime_safe(executed_at_str, date_fmt)

    quantity = parse_decimal_safe(
        row.get(get_mapped_col(columns, "quantity", op_type, csv_action)),
        decimal_separator,
    )
    quantity = apply_transformation(transformations, "quantity", quantity, op_type, csv_action)

    unit_price = parse_decimal_safe(
        row.get(get_mapped_col(columns, "unit_price", op_type, csv_action)),
        decimal_separator,
    )
    unit_price = apply_transformation(transformations, "unit_price", unit_price, op_type, csv_action)

    total_amount = parse_decimal_safe(
        row.get(get_mapped_col(columns, "total_amount", op_type, csv_action)),
        decimal_separator,
    )
    total_amount = apply_transformation(transformations, "total_amount", total_amount, op_type, csv_action)
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

    exchange_rate = parse_decimal_safe(
        row.get(get_mapped_col(columns, "exchange_rate", op_type, csv_action)),
        decimal_separator,
    )

    # Child Fees and Taxes
    fees = []
    fee_amt_col = get_mapped_col(columns, "fee_amount", op_type, csv_action)
    if fee_amt_col:
        fee_val = parse_decimal_safe(row.get(fee_amt_col), decimal_separator)
        fee_val = apply_transformation(transformations, "fee_amount", fee_val, op_type, csv_action)
        if fee_val and fee_val > 0:
            fee_curr = row.get(get_mapped_col(columns, "fee_currency", op_type, csv_action)) or currency
            resolved_fee_type = "conversion"
            fee_type_col = get_mapped_col(columns, "fee_type", op_type, csv_action)
            if fee_type_col:
                raw_fee_type = row.get(fee_type_col)
                if raw_fee_type:
                    fee_type_mappings = schema_mappings.get("enum_mappings", {}).get("fee_type", {})
                    for key, val_list in fee_type_mappings.items():
                        if raw_fee_type in val_list or raw_fee_type == key:
                            resolved_fee_type = key
                            break
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
            resolved_tax_type = "withholding_tax"
            fee_type_col = get_mapped_col(columns, "fee_type", op_type, csv_action)
            if fee_type_col:
                raw_fee_type = row.get(fee_type_col)
                if raw_fee_type:
                    fee_type_mappings = schema_mappings.get("enum_mappings", {}).get("fee_type", {})
                    for key, val_list in fee_type_mappings.items():
                        if raw_fee_type in val_list or raw_fee_type == key:
                            resolved_tax_type = key
                            break
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

    # Merchant fields
    merchant_name = row.get(get_mapped_col(columns, "merchant_name", op_type, csv_action))
    merchant_category = row.get(get_mapped_col(columns, "merchant_category", op_type, csv_action))

    # Reference fields
    source_ref_col = get_mapped_col(columns, "source_reference", op_type, csv_action)
    source_reference = row.get(source_ref_col) if source_ref_col else None
    dest_ref_col = get_mapped_col(columns, "destination_reference", op_type, csv_action)
    destination_reference = row.get(dest_ref_col) if dest_ref_col else None

    if op_type == "transfer_in" and not source_reference:
        source_reference = notes or "CSV Import"
    if op_type == "transfer_out" and not destination_reference:
        destination_reference = notes or "CSV Import"

    dividend_per_share = unit_price if op_type == "dividend" else None

    # Trade resolution
    if op_type == "trade":
        if not trade_side:
            trade_side_col = get_mapped_col(columns, "trade_side", op_type, csv_action)
            raw_trade_side = row.get(trade_side_col) if trade_side_col else None
            if raw_trade_side:
                trade_side_mappings = schema_mappings.get("enum_mappings", {}).get("trade_side", {})
                for key, val_list in trade_side_mappings.items():
                    if raw_trade_side in val_list or raw_trade_side == key:
                        trade_side = key
                        break
            if not trade_side:
                trade_side = "buy"

        if not order_type_val:
            order_type_col = get_mapped_col(columns, "order_type", op_type, csv_action)
            raw_order_type = row.get(order_type_col) if order_type_col else None
            if raw_order_type:
                order_type_mappings = schema_mappings.get("enum_mappings", {}).get("order_type", {})
                for key, val_list in order_type_mappings.items():
                    if raw_order_type in val_list or raw_order_type == key:
                        order_type_val = key
                        break
            if not order_type_val:
                order_type_val = "market"

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
        if raw_order_status:
            os_mappings = schema_mappings.get("enum_mappings", {}).get("order_status", {})
            for key, val_list in os_mappings.items():
                if raw_order_status in val_list or raw_order_status == key:
                    order_status = key
                    break
        if not order_status:
            order_status = "filled"

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

    expense_category = None
    revenue_category = None
    payment_method = None
    if op_type == "expense":
        ec_col = get_mapped_col(columns, "expense_category", op_type, csv_action)
        raw_ec = row.get(ec_col) if ec_col else None
        if raw_ec:
            ec_mappings = schema_mappings.get("enum_mappings", {}).get("expense_category", {})
            for key, val_list in ec_mappings.items():
                if raw_ec in val_list or raw_ec == key:
                    expense_category = key
                    break
        if not expense_category:
            expense_category = "other"
    elif op_type == "revenue":
        rc_col = get_mapped_col(columns, "revenue_category", op_type, csv_action)
        raw_rc = row.get(rc_col) if rc_col else None
        if raw_rc:
            rc_mappings = schema_mappings.get("enum_mappings", {}).get("revenue_category", {})
            for key, val_list in rc_mappings.items():
                if raw_rc in val_list or raw_rc == key:
                    revenue_category = key
                    break
        if not revenue_category:
            revenue_category = "other"

    if op_type in ("expense", "revenue"):
        pm_col = get_mapped_col(columns, "payment_method", op_type, csv_action)
        raw_pm = row.get(pm_col) if pm_col else None
        if raw_pm:
            pm_mappings = schema_mappings.get("enum_mappings", {}).get("payment_method", {})
            for key, val_list in pm_mappings.items():
                if raw_pm in val_list or raw_pm == key:
                    payment_method = key
                    break

    fee_category = notes or "other" if op_type == "fee" else None
    tax_category = notes or "withholding" if op_type == "tax" else None

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

    return {
        "op_type": op_type,
        "ticker": ticker,
        "isin": isin,
        "name": name,
        "quantity": quantity,
        "unit_price": unit_price,
        "price_currency": price_currency,
        "total_amount": total_amount,
        "currency": currency,
        "executed_at": executed_at,
        "notes": notes,
        "transaction_id": transaction_id,
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
    }
