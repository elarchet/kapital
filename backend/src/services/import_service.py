from __future__ import annotations

import contextlib
import csv
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict

from sqlmodel import Session, select

from src.crud import (
    import_file_schema_crud,
    operation_crud,
    position_crud,
)
from src.models import (
    AssetType,
    Fee,
    FeeType,
    FinancialAccount,
    Institution,
    Operation,
    Position,
)
from src.schemas.fee import FeeCreate
from src.schemas.operation import OperationCreate
from src.schemas.position import PositionCreate


class ImportSummary(TypedDict):
    positions_created: int
    operations_imported: int
    operations_skipped: int


def autodetect_schema(db: Session, headers: list[str], user_id: int) -> int | None:
    """Compare CSV headers with known mappings to auto-detect the template schema.

    Returns the ID of the best-matching schema, or None.
    """
    schemas = import_file_schema_crud.get_multi_by_user_or_public(db, user_id=user_id)
    best_schema_id = None
    max_matches = 0

    headers_set = {h.strip().lower() for h in headers}

    for schema in schemas:
        try:
            mapping_dict = json.loads(schema.mappings)
            columns = mapping_dict.get("columns", {})
            if not columns:
                continue

            # Count how many mapped column headers exist in the CSV headers
            mapped_headers = {str(val).strip().lower() for val in columns.values() if val}
            matches = len(headers_set.intersection(mapped_headers))

            # Require at least 5 matching headers to avoid false positives
            if matches >= 5 and matches > max_matches:  # noqa: PLR2004
                max_matches = matches
                best_schema_id = schema.id
        except Exception:  # noqa: BLE001, S112
            continue

    return best_schema_id


def parse_decimal_safe(val: str | None, decimal_sep: str = ".") -> Decimal | None:
    """Parse a string to Decimal safely, replacing decimal separator if needed."""
    if not val or not val.strip():
        return None
    cleaned = val.strip()
    if decimal_sep != ".":
        cleaned = cleaned.replace(decimal_sep, ".")
    # Remove any thousands separators (commas if decimal is dot, or dots/spaces)
    cleaned = cleaned.replace(",", "") if decimal_sep == "." else cleaned.replace(".", "").replace(" ", "")

    try:
        return Decimal(cleaned)
    except Exception:  # noqa: BLE001
        return None


def parse_datetime_safe(val: str) -> datetime:
    """Parse string timestamp dynamically supporting ISO and common formats."""
    cleaned = val.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(cleaned, fmt)  # noqa: DTZ007
        except ValueError:
            continue
    # Fallback to standard isoformat
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return datetime.now(UTC)


def import_portfolio_transactions(  # noqa: C901, PLR0912, PLR0915
    db: Session,
    portfolio_id: int,
    user_id: int,
    file_content: bytes,
    schema_id: int | None = None,
    custom_schema_config: dict | None = None,
) -> ImportSummary:
    """Parse uploaded file content and import operations/positions for a portfolio."""
    # 1. Resolve Import Schema
    schema_mappings = {}
    delimiter = ","
    decimal_separator = "."

    if schema_id is not None:
        schema = import_file_schema_crud.get_by_owner_or_public(db, id=schema_id, user_id=user_id)
        if not schema:
            raise ValueError(f"Import schema with id {schema_id} not found.")
        schema_mappings = json.loads(schema.mappings)
        delimiter = schema.delimiter
        decimal_separator = schema.decimal_separator
    elif custom_schema_config is not None:
        schema_mappings = custom_schema_config.get("mappings", {})
        delimiter = custom_schema_config.get("delimiter", ",")
        decimal_separator = custom_schema_config.get("decimal_separator", ".")
    else:
        raise ValueError("Either schema_id or custom_schema_config must be provided.")

    columns = schema_mappings.get("columns", {})
    type_mappings = schema_mappings.get("type_mappings", {})
    scaling = schema_mappings.get("scaling", {})
    transformations = schema_mappings.get("transformations", {})

    # 2. Setup Default Institution and Financial Account
    institution_name = schema_mappings.get("institution_name", "Trading 212")
    account_name = schema_mappings.get("account_name", "Trading 212 Account")

    institution = db.exec(select(Institution).where(Institution.name == institution_name)).first()
    if not institution:
        institution = Institution(name=institution_name, country="GB")
        db.add(institution)
        db.commit()
        db.refresh(institution)

    if institution.id is None:
        raise ValueError("Institution ID not resolved.")

    financial_account = db.exec(
        select(FinancialAccount).where(
            FinancialAccount.name == account_name,
            FinancialAccount.institution_id == institution.id,
        ),
    ).first()
    if not financial_account:
        financial_account = FinancialAccount(
            name=account_name,
            currency="EUR",
            institution_id=institution.id,
        )
        db.add(financial_account)
        db.commit()
        db.refresh(financial_account)

    if financial_account.id is None:
        raise ValueError("Financial account ID not resolved.")

    # 3. Decode & Parse CSV rows
    decoded = file_content.decode("utf-8-sig")
    reader = csv.DictReader(decoded.splitlines(), delimiter=delimiter)

    raw_rows = list(reader)

    # 4. Process Rows Chronologically
    # Map raw rows to parsed operations
    def apply_transformation(col_name: str, val: Decimal | None) -> Decimal | None:
        if val is None:
            return None
        trans = transformations.get(col_name, {})
        divisor_val = trans.get("divisor")
        if divisor_val:
            with contextlib.suppress(ArithmeticError, ValueError, TypeError):
                val /= Decimal(str(divisor_val))
        multiplier_val = trans.get("multiplier")
        if multiplier_val:
            with contextlib.suppress(ArithmeticError, ValueError, TypeError):
                val *= Decimal(str(multiplier_val))
        return val

    parsed_operations = []
    for row in raw_rows:
        # Get transaction type from CSV action column
        csv_action = row.get(columns.get("operation_type", "Action"))
        if not csv_action:
            continue

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
            continue

        # Extract values
        ticker = row.get(columns.get("ticker", "Ticker"))
        isin = row.get(columns.get("isin", "ISIN"))
        name = row.get(columns.get("name", "Name")) or ticker or isin or "Asset"
        notes = row.get(columns.get("notes", "Notes"))
        transaction_id = row.get(columns.get("transaction_id", "ID"))
        currency = row.get(columns.get("currency", "Currency (Total)")) or "EUR"

        executed_at_str = row.get(columns.get("executed_at", "Time"))
        if not executed_at_str:
            continue
        executed_at = parse_datetime_safe(executed_at_str)

        quantity = parse_decimal_safe(row.get(columns.get("quantity", "No. of shares")), decimal_separator)
        quantity = apply_transformation("quantity", quantity)

        unit_price = parse_decimal_safe(row.get(columns.get("unit_price", "Price / share")), decimal_separator)
        unit_price = apply_transformation("unit_price", unit_price)

        total_amount = parse_decimal_safe(row.get(columns.get("total_amount", "Total")), decimal_separator)
        total_amount = apply_transformation("total_amount", total_amount)
        if total_amount is None:
            total_amount = Decimal(0)

        # Apply scaling based on currency (e.g. GBX to GBP)
        price_currency = row.get(columns.get("price_currency", "Currency (Price / share)")) or currency
        if price_currency in scaling.get("unit_price", {}):
            factor = Decimal(str(scaling["unit_price"][price_currency]))
            if unit_price:
                unit_price *= factor
        if currency in scaling.get("total_amount", {}):
            factor = Decimal(str(scaling["total_amount"][currency]))
            total_amount *= factor
            # Change currency symbol if scaled
            if currency == "GBX":
                currency = "GBP"

        # Exchange rate
        exchange_rate = parse_decimal_safe(row.get(columns.get("exchange_rate", "Exchange rate")), decimal_separator)

        # Child Fees and Taxes
        fees = []
        fee_amt_col = columns.get("fee_amount")
        if fee_amt_col:
            fee_val = parse_decimal_safe(row.get(fee_amt_col), decimal_separator)
            fee_val = apply_transformation("fee_amount", fee_val)
            if fee_val and fee_val > 0:
                fee_curr = row.get(columns.get("fee_currency")) or currency

                # Resolve fee_type if mapped
                resolved_fee_type = "conversion"
                fee_type_col = columns.get("fee_type")
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

        tax_amt_col = columns.get("tax_amount")
        if tax_amt_col:
            tax_val = parse_decimal_safe(row.get(tax_amt_col), decimal_separator)
            tax_val = apply_transformation("tax_amount", tax_val)
            if tax_val and tax_val > 0:
                tax_curr = row.get(columns.get("tax_currency")) or currency

                # Resolve tax type
                resolved_tax_type = "withholding_tax"
                fee_type_col = columns.get("fee_type")
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
        merchant_name = row.get(columns.get("merchant_name"))
        merchant_category = row.get(columns.get("merchant_category"))

        # Source / destination reference for transfer_in / transfer_out
        source_ref_col = columns.get("source_reference")
        source_reference = row.get(source_ref_col) if source_ref_col else None
        dest_ref_col = columns.get("destination_reference")
        destination_reference = row.get(dest_ref_col) if dest_ref_col else None

        if op_type == "transfer_in" and not source_reference:
            source_reference = notes or "CSV Import"
        if op_type == "transfer_out" and not destination_reference:
            destination_reference = notes or "CSV Import"

        # Dividend per share
        dividend_per_share = None
        if op_type == "dividend":
            dividend_per_share = unit_price

        # Limit price
        limit_price = None
        if op_type in ("limit_buy", "limit_sell"):
            limit_price = unit_price

        # Fee / tax categories
        fee_category = None
        if op_type == "fee":
            fee_category = notes or "other"
        tax_category = None
        if op_type == "tax":
            tax_category = notes or "withholding"

        # FX rate change parsing (e.g. source_currency, target_currency, exchange_rate)
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
                source_currency = row.get(columns.get("source_currency", "Currency (Currency conversion from amount)"))
                target_currency = row.get(columns.get("target_currency", "Currency (Currency conversion to amount)"))
                if source_currency:
                    source_currency = source_currency.strip()
                if target_currency:
                    target_currency = target_currency.strip()
                if not exchange_rate:
                    from_amt = parse_decimal_safe(
                        row.get(columns.get("from_amount", "Currency conversion from amount")),
                        decimal_separator,
                    )
                    to_amt = parse_decimal_safe(
                        row.get(columns.get("to_amount", "Currency conversion to amount")),
                        decimal_separator,
                    )
                    if from_amt and to_amt and from_amt > 0:
                        exchange_rate = to_amt / from_amt

            if not source_currency:
                source_currency = currency
            if not target_currency:
                target_currency = currency
            if not exchange_rate:
                exchange_rate = Decimal("1.0")

        parsed_operations.append(
            {
                "op_type": op_type,
                "ticker": ticker,
                "isin": isin,
                "name": name,
                "quantity": quantity,
                "unit_price": unit_price,
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
            },
        )

    # Sort operations chronologically
    parsed_operations.sort(key=lambda o: o["executed_at"])

    # 5. Group Stock Splits
    # Trading 212 models stock splits as Stock split close and Stock split open
    # We combine them if they occur on the same asset at the same second
    processed_ops = []
    skip_indices = set()

    for i in range(len(parsed_operations)):
        if i in skip_indices:
            continue

        op_data = parsed_operations[i]

        # Check if this is a stock split close row and the next row is a stock split open for same asset
        is_split_close = op_data["csv_action"] == "Stock split close"
        if is_split_close and i + 1 < len(parsed_operations):
            next_op = parsed_operations[i + 1]
            if (
                next_op["csv_action"] == "Stock split open"
                and next_op["ticker"] == op_data["ticker"]
                and abs((next_op["executed_at"] - op_data["executed_at"]).total_seconds()) <= 60  # noqa: PLR2004
            ):
                # We have a matching split pair! Combine them
                close_qty = op_data["quantity"] or Decimal(1)
                open_qty = next_op["quantity"] or Decimal(1)
                split_ratio = open_qty / close_qty

                # Merge into a single stock split operation
                op_data["op_type"] = "stock_split"
                op_data["split_ratio"] = split_ratio
                op_data["quantity"] = open_qty - close_qty  # Net quantity added
                op_data["notes"] = f"Stock split 1 to {split_ratio:.4f}"
                skip_indices.add(i + 1)

        processed_ops.append(op_data)

    # 6. Execute DB insertions and update positions
    summary: ImportSummary = {
        "positions_created": 0,
        "operations_imported": 0,
        "operations_skipped": 0,
    }

    for op_info in processed_ops:
        transaction_id = op_info["transaction_id"]

        # Check if asset is stock/ETF vs. cash
        is_cash_op = (
            op_info["op_type"] in ("interest", "transfer_in", "transfer_out", "expense", "revenue")
            and not op_info["ticker"]
        )

        # Find or create Position
        position = None
        if not is_cash_op:
            # Stock / ETF Position
            # Search by ISIN or Ticker in portfolio
            statement = select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.is_active == True,  # noqa: E712
            )
            if op_info["isin"]:
                statement = statement.where(Position.isin == op_info["isin"])
            elif op_info["ticker"]:
                statement = statement.where(Position.ticker == op_info["ticker"])
            else:
                statement = statement.where(Position.name == op_info["name"])

            position = db.exec(statement).first()

            if not position:
                # Infer ETF vs Stock
                asset_type = AssetType.STOCK
                lower_name = op_info["name"].lower()
                if (
                    "etf" in lower_name
                    or "ishares" in lower_name
                    or "vanguard" in lower_name
                    or "xtrackers" in lower_name
                ):
                    asset_type = AssetType.ETF

                position_in = PositionCreate(
                    portfolio_id=portfolio_id,
                    asset_type=asset_type,
                    ticker=op_info["ticker"],
                    name=op_info["name"],
                    isin=op_info["isin"],
                    quantity=Decimal("0.0"),
                    currency=op_info["currency"],
                )
                position = position_crud.create(db, obj_in=position_in)
                summary["positions_created"] += 1
        else:
            # Cash Position
            cash_currency = op_info["currency"]
            cash_name = f"Cash ({cash_currency})"
            position = db.exec(
                select(Position).where(
                    Position.portfolio_id == portfolio_id,
                    Position.asset_type == AssetType.CASH,
                    Position.currency == cash_currency,
                    Position.is_active == True,  # noqa: E712
                ),
            ).first()

            if not position:
                position_in = PositionCreate(
                    portfolio_id=portfolio_id,
                    asset_type=AssetType.CASH,
                    name=cash_name,
                    quantity=Decimal("0.0"),
                    currency=cash_currency,
                )
                position = position_crud.create(db, obj_in=position_in)
                summary["positions_created"] += 1

        # Skip if position not created/found (safety check)
        if not position or position.id is None:
            continue

        # Duplicate Check: Check if transaction already exists (with composite check fallback)
        if transaction_id:
            existing_op = db.exec(select(Operation).where(Operation.transaction_id == transaction_id)).first()
            if existing_op:
                summary["operations_skipped"] += 1
                continue
        else:
            statement = select(Operation).where(
                Operation.position_id == position.id,
                Operation.operation_type == op_info["op_type"],
                Operation.executed_at == op_info["executed_at"],
                Operation.total_amount == op_info["total_amount"],
            )
            if op_info["quantity"] is not None:
                statement = statement.where(Operation.quantity == op_info["quantity"])
            else:
                statement = statement.where(Operation.quantity.is_(None))

            existing_op = db.exec(statement).first()
            if existing_op:
                summary["operations_skipped"] += 1
                continue

        # Create Operation
        op_in = OperationCreate(
            operation_type=op_info["op_type"],
            quantity=op_info["quantity"],
            unit_price=op_info["unit_price"],
            total_amount=op_info["total_amount"],
            currency=op_info["currency"],
            executed_at=op_info["executed_at"],
            notes=op_info["notes"],
            position_id=position.id,
            financial_account_id=financial_account.id,
            transaction_id=transaction_id,
            exchange_rate=op_info["exchange_rate"],
            split_ratio=op_info.get("split_ratio"),
            merchant_name=op_info.get("merchant_name"),
            merchant_category=op_info.get("merchant_category"),
            source_reference=op_info.get("source_reference"),
            destination_reference=op_info.get("destination_reference"),
            dividend_per_share=op_info.get("dividend_per_share"),
            limit_price=op_info.get("limit_price"),
            fee_category=op_info.get("fee_category"),
            tax_category=op_info.get("tax_category"),
            source_currency=op_info.get("source_currency"),
            target_currency=op_info.get("target_currency"),
        )

        db_op = operation_crud.create(db, obj_in=op_in)

        # Create Child Fees
        for fee_in in op_info["fees"]:
            db_fee = Fee(
                amount=fee_in.amount,
                currency=fee_in.currency,
                fee_type=fee_in.fee_type,
                notes=fee_in.notes,
                operation_id=db_op.id,
            )
            db.add(db_fee)
            db.commit()

        # Update Position quantity
        if op_info["op_type"] in ("buy", "limit_buy"):
            position.quantity += op_info["quantity"]
        elif op_info["op_type"] in ("sell", "limit_sell"):
            position.quantity -= op_info["quantity"]
        elif op_info["op_type"] == "stock_split":
            # For split, net quantity is added/removed
            position.quantity += op_info["quantity"]
        elif is_cash_op:
            # Interest, Card debits, Deposits directly update cash balance
            # For Expense/Revenue, total_amount is already signed
            # (Interest/Deposits are positive, Card debits are negative)
            position.quantity += op_info["total_amount"]

        db.add(position)
        db.commit()

        # Update Cash Position balance for stock buys/sells
        if not is_cash_op:
            cash_currency = op_info["currency"]
            cash_pos = db.exec(
                select(Position).where(
                    Position.portfolio_id == portfolio_id,
                    Position.asset_type == AssetType.CASH,
                    Position.currency == cash_currency,
                    Position.is_active == True,  # noqa: E712
                ),
            ).first()

            if not cash_pos:
                cash_name = f"Cash ({cash_currency})"
                position_in = PositionCreate(
                    portfolio_id=portfolio_id,
                    asset_type=AssetType.CASH,
                    name=cash_name,
                    quantity=Decimal("0.0"),
                    currency=cash_currency,
                )
                cash_pos = position_crud.create(db, obj_in=position_in)
                summary["positions_created"] += 1

            if cash_pos and cash_pos.id is not None:
                if op_info["op_type"] in ("buy", "limit_buy"):
                    # Buys decrease cash (total_amount is positive cost)
                    cash_pos.quantity -= op_info["total_amount"]
                elif op_info["op_type"] in ("sell", "limit_sell"):
                    # Sells increase cash (total_amount is positive gain)
                    cash_pos.quantity += op_info["total_amount"]
                elif op_info["op_type"] == "dividend":
                    # Dividends increase cash
                    cash_pos.quantity += op_info["total_amount"]

                db.add(cash_pos)
                db.commit()

        summary["operations_imported"] += 1

    return summary
