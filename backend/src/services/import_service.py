"""Import orchestration — parse an institution export into RawTransactions.

Pipeline:
    decode CSV -> parse rows -> combine splits -> enrich ->
    dedup (idempotency) -> RawTransaction + default Allocation -> update Position

Every uploaded file is assumed to originate from a single institution (chosen
via the import template). Transactions are deduplicated per financial account
using a hardened, deterministic dedup key.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from typing import TYPE_CHECKING, TypedDict

from sqlmodel import select

from src.logic.idempotency import RowValidationError, compute_dedup_key
from src.models import Fee, ImportFileSchema, Institution
from src.services.allocation_service import make_default_allocation
from src.services.financial_info import FinancialInfoService
from src.services.import_db import (
    PositionCache,
    build_raw_transaction,
    get_or_create_institution_and_account,
    load_existing_dedup_keys,
)
from src.services.import_enrichment import run_enrichment_pipeline
from src.services.import_parsers import combine_stock_splits
from src.services.import_row_parser import parse_csv_row
from src.services.institutions import get_profile

if TYPE_CHECKING:
    from sqlmodel import Session

    from src.models import FinancialAccount, Position

_CASH_OP_TYPES = ("interest", "transfer_in", "transfer_out", "expense", "revenue")


class ImportSummary(TypedDict):
    positions_created: int
    raw_transactions_imported: int
    allocations_created: int
    skipped_duplicates: int
    skipped_invalid: int


def autodetect_schema(db: Session, headers: list[str], user_id: int) -> int | None:
    """Compare CSV headers with known mappings to auto-detect the template schema."""
    statement = select(ImportFileSchema).where(
        (ImportFileSchema.user_id == user_id) | ImportFileSchema.is_public,
        ImportFileSchema.is_active == True,  # noqa: E712
    )
    schemas = list(db.exec(statement).all())
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


def _resolve_schema_config(
    db: Session,
    user_id: int,
    schema_id: int | None,
    custom_schema_config: dict | None,
) -> tuple[dict, str, str, str]:
    """Return (mappings, delimiter, decimal_separator, institution_key)."""
    if schema_id is not None:
        statement = select(ImportFileSchema).where(
            ImportFileSchema.id == schema_id,
            (ImportFileSchema.user_id == user_id) | ImportFileSchema.is_public,
            ImportFileSchema.is_active == True,  # noqa: E712
        )
        schema = db.exec(statement).first()
        if not schema:
            raise ValueError(f"Import schema with id {schema_id} not found.")
        return (
            json.loads(schema.mappings),
            schema.delimiter,
            schema.decimal_separator,
            schema.institution_key,
        )
    if custom_schema_config is not None:
        mappings = custom_schema_config.get("mappings", {})
        return (
            mappings,
            custom_schema_config.get("delimiter", ","),
            custom_schema_config.get("decimal_separator", "."),
            custom_schema_config.get("institution_key", mappings.get("institution_key", "custom")),
        )
    raise ValueError("Either schema_id or custom_schema_config must be provided.")


def _resolve_account(db: Session, mappings: dict, institution_key: str) -> FinancialAccount:
    """Resolve the target financial account from the institution abstraction."""
    profile = get_profile(institution_key)
    default_inst = profile.name if profile else "Imported Institution"
    default_acct = profile.default_account_name if profile else "Imported Account"
    country = profile.country if profile else None

    institution_id = mappings.get("institution_id")
    if institution_id is not None:
        institution = db.get(Institution, institution_id)
        if institution is not None:
            default_inst = institution.name
            default_acct = f"{institution.name} Account"
            country = institution.country

    institution_name = mappings.get("institution_name") or default_inst
    account_name = mappings.get("account_name") or default_acct
    return get_or_create_institution_and_account(db, institution_name, account_name, country=country)


def _parse_rows(decoded: str, delimiter: str, mappings: dict, decimal_separator: str) -> list[dict]:
    """Decode and parse every CSV row into canonical op_info dicts."""
    columns = mappings.get("columns", {})
    reader = csv.DictReader(decoded.splitlines(), delimiter=delimiter)
    parsed: list[dict] = []
    for row in reader:
        op = parse_csv_row(
            row=row,
            columns=columns,
            type_mappings=mappings.get("type_mappings", {}),
            scaling=mappings.get("scaling", {}),
            transformations=mappings.get("transformations", {}),
            date_formats=mappings.get("date_formats", {}),
            schema_mappings=mappings,
            decimal_separator=decimal_separator,
        )
        if op:
            parsed.append(op)
    return parsed


def _apply_balances(op_info: dict, position: Position, cache: PositionCache, *, is_cash_op: bool) -> None:
    """Update running position (and cash) balances for a single transaction."""
    trade_side = op_info.get("trade_side")
    is_buy = op_info["op_type"] == "trade" and trade_side == "buy"
    is_sell = op_info["op_type"] == "trade" and trade_side == "sell"
    quantity = op_info.get("quantity") or Decimal(0)
    total_amount = op_info.get("total_amount") or Decimal(0)

    if is_buy:
        position.quantity += quantity
    elif is_sell:
        position.quantity -= quantity
    elif op_info["op_type"] == "stock_split":
        position.quantity += quantity
    elif is_cash_op:
        position.quantity += total_amount

    if not is_cash_op:
        cash_pos = cache.get_or_create_cash(op_info["currency"])
        if is_buy:
            cash_pos.quantity -= total_amount
        elif is_sell or op_info["op_type"] == "dividend":
            cash_pos.quantity += total_amount


async def import_portfolio_transactions(
    db: Session,
    portfolio_id: int,
    user_id: int,
    file_content: bytes,
    schema_id: int | None = None,
    custom_schema_config: dict | None = None,
) -> ImportSummary:
    """Parse an uploaded institution export and ingest it into a portfolio."""
    mappings, delimiter, decimal_separator, institution_key = _resolve_schema_config(
        db,
        user_id,
        schema_id,
        custom_schema_config,
    )
    # Fall back to the built-in institution profile when the template carries no
    # column mappings of its own.
    if not mappings.get("columns"):
        profile = get_profile(institution_key)
        if profile:
            mappings = {**profile.mappings, **mappings}
    account = _resolve_account(db, mappings, institution_key)

    try:
        decoded = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Some broker exports (e.g. Fortuneo) ship Latin-1 instead of UTF-8.
        decoded = file_content.decode("latin-1")
    parsed_operations = _parse_rows(decoded, delimiter, mappings, decimal_separator)
    parsed_operations.sort(key=lambda o: o["executed_at"])
    processed_ops = combine_stock_splits(parsed_operations)

    financial_info = FinancialInfoService()
    await run_enrichment_pipeline(processed_ops, mappings, financial_info, db)

    cache = PositionCache(db, portfolio_id)
    existing_keys = load_existing_dedup_keys(db, account.id)

    summary: ImportSummary = {
        "positions_created": 0,
        "raw_transactions_imported": 0,
        "allocations_created": 0,
        "skipped_duplicates": 0,
        "skipped_invalid": 0,
    }

    scope = str(account.id)
    try:
        for op_info in processed_ops:
            raw_row = op_info.get("_raw_row") or {}
            try:
                # _hash_row is the user-selected column subset (falls back to the full row).
                dedup_key, is_native = compute_dedup_key(
                    op_info.get("_hash_row") or raw_row,
                    scope=scope,
                    native_id=op_info.get("native_transaction_id"),
                )
            except RowValidationError:
                summary["skipped_invalid"] += 1
                continue

            if dedup_key in existing_keys:
                summary["skipped_duplicates"] += 1
                continue
            existing_keys.add(dedup_key)

            is_cash_op = op_info["op_type"] in _CASH_OP_TYPES and not op_info.get("ticker")
            position = (
                cache.get_or_create_cash(op_info["currency"]) if is_cash_op else cache.get_or_create_asset(op_info)
            )

            raw_txn = build_raw_transaction(
                op_info,
                dedup_key=dedup_key,
                is_auto_id=not is_native,
                native_transaction_id=op_info.get("native_transaction_id"),
                financial_account_id=account.id,
                raw_payload=raw_row,
            )
            if op_info.get("fees"):
                raw_txn.fees = [
                    Fee(
                        amount=fee_in.amount,
                        currency=fee_in.currency,
                        fee_type=fee_in.fee_type,
                        notes=fee_in.notes,
                    )
                    for fee_in in op_info["fees"]
                ]
            db.add(raw_txn)

            allocation = make_default_allocation(raw_txn, position, op_info)
            db.add(allocation)
            summary["allocations_created"] += 1

            _apply_balances(op_info, position, cache, is_cash_op=is_cash_op)
            summary["raw_transactions_imported"] += 1

        summary["positions_created"] = cache.created
        db.commit()
    except Exception:
        db.rollback()
        raise

    return summary
