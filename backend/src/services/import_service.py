from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from sqlmodel import Session

from src.crud import import_file_schema_crud, operation_crud
from src.models import Fee
from src.schemas.operation import OperationCreate
from src.services.import_db import (
    check_duplicate_operation,
    find_or_create_position,
    get_or_create_cash_position,
    get_or_create_institution_and_account,
)
from src.services.import_parsers import combine_stock_splits
from src.services.import_row_parser import parse_csv_row


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

            mapped_headers = {str(val).strip().lower() for val in columns.values() if val}
            matches = len(headers_set.intersection(mapped_headers))

            if matches >= 5 and matches > max_matches:  # noqa: PLR2004
                max_matches = matches
                best_schema_id = schema.id
        except Exception:  # noqa: BLE001, S112
            continue

    return best_schema_id


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
    date_formats = schema_mappings.get("date_formats", {})

    # 2. Setup Default Institution and Financial Account
    institution_name = schema_mappings.get("institution_name", "Trading 212")
    account_name = schema_mappings.get("account_name", "Trading 212 Account")
    financial_account = get_or_create_institution_and_account(db, institution_name, account_name)

    # 3. Decode & Parse CSV rows
    decoded = file_content.decode("utf-8-sig")
    reader = csv.DictReader(decoded.splitlines(), delimiter=delimiter)
    raw_rows = list(reader)

    # 4. Process Rows Chronologically
    parsed_operations = []
    for row in raw_rows:
        parsed_op = parse_csv_row(
            row=row,
            columns=columns,
            type_mappings=type_mappings,
            scaling=scaling,
            transformations=transformations,
            date_formats=date_formats,
            schema_mappings=schema_mappings,
            decimal_separator=decimal_separator,
        )
        if parsed_op:
            parsed_operations.append(parsed_op)

    parsed_operations.sort(key=lambda o: o["executed_at"])
    processed_ops = combine_stock_splits(parsed_operations)

    # 5. Execute DB insertions and update positions
    summary: ImportSummary = {
        "positions_created": 0,
        "operations_imported": 0,
        "operations_skipped": 0,
    }

    for op_info in processed_ops:
        is_cash_op = (
            op_info["op_type"] in ("interest", "transfer_in", "transfer_out", "expense", "revenue")
            and not op_info["ticker"]
        )

        # Find or create Position
        position, pos_created = find_or_create_position(db, portfolio_id, op_info, is_cash_op=is_cash_op)
        if pos_created:
            summary["positions_created"] += 1

        if not position or position.id is None:
            continue

        # Duplicate check
        if check_duplicate_operation(db, position.id, op_info):
            summary["operations_skipped"] += 1
            continue

        # Create Operation
        op_in = OperationCreate(
            operation_type=op_info["op_type"],
            quantity=op_info["quantity"],
            unit_price=op_info["unit_price"],
            price_currency=op_info.get("price_currency"),
            total_amount=op_info["total_amount"],
            currency=op_info["currency"],
            executed_at=op_info["executed_at"],
            notes=op_info["notes"],
            position_id=position.id,
            financial_account_id=financial_account.id,
            transaction_id=op_info["transaction_id"],
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
            trade_side=op_info.get("trade_side"),
            order_type=op_info.get("order_type"),
            order_status=op_info.get("order_status"),
            stop_price=op_info.get("stop_price"),
            execution_price=op_info.get("execution_price"),
            order_placed_at=op_info.get("order_placed_at"),
            filled_at=op_info.get("filled_at"),
            expense_category=op_info.get("expense_category"),
            revenue_category=op_info.get("revenue_category"),
            payment_method=op_info.get("payment_method"),
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
        is_buy_trade = op_info["op_type"] == "trade" and op_info.get("trade_side") == "buy"
        is_sell_trade = op_info["op_type"] == "trade" and op_info.get("trade_side") == "sell"

        if is_buy_trade:
            position.quantity += op_info["quantity"]
        elif is_sell_trade:
            position.quantity -= op_info["quantity"]
        elif op_info["op_type"] == "stock_split":
            position.quantity += op_info["quantity"]
        elif is_cash_op:
            position.quantity += op_info["total_amount"]

        db.add(position)
        db.commit()

        # Update Cash Position balance for stock trades/dividends
        if not is_cash_op:
            cash_currency = op_info["currency"]
            cash_pos, cash_created = get_or_create_cash_position(db, portfolio_id, cash_currency)
            if cash_created:
                summary["positions_created"] += 1

            if cash_pos and cash_pos.id is not None:
                if is_buy_trade:
                    cash_pos.quantity -= op_info["total_amount"]
                elif is_sell_trade or op_info["op_type"] == "dividend":
                    cash_pos.quantity += op_info["total_amount"]

                db.add(cash_pos)
                db.commit()

        summary["operations_imported"] += 1

    return summary
