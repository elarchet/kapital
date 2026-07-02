from __future__ import annotations

import csv
import json
from decimal import Decimal
from typing import TYPE_CHECKING, TypedDict

from sqlmodel import select

if TYPE_CHECKING:
    from sqlmodel import Session

from src.crud import import_file_schema_crud
from src.crud.operation import OPERATION_TYPE_MAP
from src.models import (
    AssetType,
    Fee,
    Operation,
    Position,
)
from src.schemas.operation import OperationCreate
from src.services.financial_info import FinancialInfoService
from src.services.import_db import get_or_create_institution_and_account
from src.services.import_enrichment import run_enrichment_pipeline
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


async def import_portfolio_transactions(  # noqa: C901, PLR0912, PLR0915
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

    # 4b. Run enrichment pipeline
    financial_info = FinancialInfoService()
    await run_enrichment_pipeline(processed_ops, schema_mappings, financial_info, db)

    # 5. Load and Cache portfolio Position records in memory
    positions = db.exec(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.is_active,
        ),
    ).all()

    isin_to_pos = {p.isin: p for p in positions if p.isin}
    ticker_to_pos = {p.ticker: p for p in positions if p.ticker}
    name_to_pos = {p.name: p for p in positions if p.name}
    cash_currency_to_pos = {p.currency: p for p in positions if p.asset_type == AssetType.CASH}

    def get_or_create_position_cached(op_info: dict, *, is_cash_op: bool) -> tuple[Position, bool]:
        created = False
        if not is_cash_op:
            position = None
            if op_info["isin"]:
                position = isin_to_pos.get(op_info["isin"])
            elif op_info["ticker"]:
                position = ticker_to_pos.get(op_info["ticker"])
            else:
                position = name_to_pos.get(op_info["name"])

            if not position:
                asset_type = AssetType.STOCK
                lower_name = op_info["name"].lower() if op_info.get("name") else ""
                if any(term in lower_name for term in ("etf", "ishares", "vanguard", "xtrackers")):
                    asset_type = AssetType.ETF

                position = Position(
                    portfolio_id=portfolio_id,
                    asset_type=asset_type,
                    ticker=op_info["ticker"],
                    name=op_info["name"],
                    isin=op_info["isin"],
                    quantity=Decimal("0.0"),
                    currency=op_info["currency"],
                )
                db.add(position)
                # Add to caches immediately
                if position.isin:
                    isin_to_pos[position.isin] = position
                if position.ticker:
                    ticker_to_pos[position.ticker] = position
                if position.name:
                    name_to_pos[position.name] = position
                created = True
        else:
            cash_currency = op_info["currency"]
            position = cash_currency_to_pos.get(cash_currency)

            if not position:
                position = Position(
                    portfolio_id=portfolio_id,
                    asset_type=AssetType.CASH,
                    name=f"Cash ({cash_currency})",
                    quantity=Decimal("0.0"),
                    currency=cash_currency,
                )
                db.add(position)
                cash_currency_to_pos[cash_currency] = position
                created = True

        return position, created

    def get_or_create_cash_position_cached(currency: str) -> tuple[Position, bool]:
        created = False
        cash_pos = cash_currency_to_pos.get(currency)

        if not cash_pos:
            cash_pos = Position(
                portfolio_id=portfolio_id,
                asset_type=AssetType.CASH,
                name=f"Cash ({currency})",
                quantity=Decimal("0.0"),
                currency=currency,
            )
            db.add(cash_pos)
            cash_currency_to_pos[currency] = cash_pos
            created = True
        return cash_pos, created

    def get_model_cls(op_type: str) -> type[Operation]:
        model_cls = OPERATION_TYPE_MAP.get(op_type)
        if not model_cls:
            raise ValueError(f"Unknown operation type: {op_type}")
        return model_cls

    # 6. Cache existing operation transaction_ids and key tuples for duplicate checks
    existing_transaction_ids: set[str] = set()
    existing_op_tuples: set[tuple] = set()

    position_ids = [p.id for p in positions if p.id is not None]
    if position_ids:
        existing_ops = db.exec(
            select(Operation).where(Operation.position_id.in_(position_ids)),
        ).all()
        for op in existing_ops:
            if op.transaction_id:
                existing_transaction_ids.add(op.transaction_id)
            existing_op_tuples.add(
                (op.position_id, op.operation_type, op.executed_at, op.total_amount, op.quantity),
            )

    # 7. Execute DB insertions and update positions in-memory
    summary: ImportSummary = {
        "positions_created": 0,
        "operations_imported": 0,
        "operations_skipped": 0,
    }

    try:
        for op_info in processed_ops:
            is_cash_op = (
                op_info["op_type"] in ("interest", "transfer_in", "transfer_out", "expense", "revenue")
                and not op_info["ticker"]
            )

            # Find or create Position
            position, pos_created = get_or_create_position_cached(op_info, is_cash_op=is_cash_op)
            if pos_created:
                summary["positions_created"] += 1

            if not position:
                continue

            # Duplicate check
            transaction_id = op_info["transaction_id"]
            is_duplicate = False
            if transaction_id:
                is_duplicate = transaction_id in existing_transaction_ids

            # If the transaction ID is auto-generated (starts with "auto-") or missing,
            # we also perform the tuple-based fallback check.
            is_auto_id = bool(transaction_id and transaction_id.startswith("auto-"))
            if not is_duplicate and (not transaction_id or is_auto_id):
                pos_key = (
                    position.id
                    if position.id is not None
                    else (position.ticker, position.isin, position.currency, position.name)
                )
                op_tuple = (
                    pos_key,
                    op_info["op_type"],
                    op_info["executed_at"],
                    op_info["total_amount"],
                    op_info["quantity"],
                )
                is_duplicate = op_tuple in existing_op_tuples

            if is_duplicate:
                summary["operations_skipped"] += 1
                continue

            # Create Operation using compressed schema initializer to save code space
            internal_keys = frozenset(("op_type", "fees", "csv_action", "split_sub_type", "name_was_set"))
            op_data_dict = {
                "operation_type": op_info["op_type"],
                "position_id": 0,  # Dummy value for validation
                "financial_account_id": financial_account.id,
                **{k: v for k, v in op_info.items() if k not in internal_keys},
            }
            op_in = OperationCreate(**op_data_dict)

            model_cls = get_model_cls(op_in.operation_type)

            # Extract data from Pydantic schema
            obj_data = op_in.model_dump()
            obj_data.pop("fees", None)
            obj_data.pop("position_id", None)  # Discard dummy position_id

            # Filter obj_data to only include attributes that are valid for the specific subclass
            mapper = model_cls.__mapper__
            valid_keys = set(mapper.attrs.keys())
            filtered_data = {k: v for k, v in obj_data.items() if k in valid_keys or hasattr(model_cls, k)}

            # Instantiate specific subclass
            db_op = model_cls(**filtered_data)
            db_op.position = position  # Link directly to the Position object

            # Convert and attach fees if provided using relationship
            if op_info["fees"]:
                db_op.fees = [
                    Fee(
                        amount=fee_in.amount,
                        currency=fee_in.currency,
                        fee_type=fee_in.fee_type,
                        notes=fee_in.notes,
                    )
                    for fee_in in op_info["fees"]
                ]

            db.add(db_op)

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

            # Update Cash Position balance for stock trades/dividends
            if not is_cash_op:
                cash_currency = op_info["currency"]
                cash_pos, cash_created = get_or_create_cash_position_cached(cash_currency)
                if cash_created:
                    summary["positions_created"] += 1

                if cash_pos:
                    if is_buy_trade:
                        cash_pos.quantity -= op_info["total_amount"]
                    elif is_sell_trade or op_info["op_type"] == "dividend":
                        cash_pos.quantity += op_info["total_amount"]

                    db.add(cash_pos)

            # Add to duplicate check caches to prevent duplicate processing
            if transaction_id:
                existing_transaction_ids.add(transaction_id)
            pos_key = (
                position.id
                if position.id is not None
                else (position.ticker, position.isin, position.currency, position.name)
            )
            existing_op_tuples.add(
                (
                    pos_key,
                    op_info["op_type"],
                    op_info["executed_at"],
                    op_info["total_amount"],
                    op_info["quantity"],
                ),
            )

            summary["operations_imported"] += 1

        # 8. Single batch commit at the very end
        db.commit()
    except Exception:
        db.rollback()
        raise

    return summary
