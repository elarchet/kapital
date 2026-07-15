"""End-to-end import tests against real broker exports in data/ (skipped if absent).

The data/ folder is gitignored (personal exports); these tests validate the
full pipeline — Latin-1 decode, formulas, hash_columns, auto IDs, dedup —
whenever the files are available locally.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from sqlmodel import select

from src.models import Portfolio, RawTransaction, User
from src.services.import_parsers import parse_decimal_safe
from src.services.import_service import import_portfolio_transactions
from tests.factories import PortfolioFactory, UserFactory

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FORTUNEO_FILES = sorted((DATA_DIR / "fortuneo").glob("*.csv")) if DATA_DIR.exists() else []
T212_FILES = sorted((DATA_DIR / "t212").glob("*2023*.csv")) if DATA_DIR.exists() else []

FORTUNEO_MAPPINGS = {
    "columns": {
        "operation_type": "Opération",
        "executed_at": "Date",
        "name": "libellé",
        "currency": "Devise",
        "quantity": "Qté",
        "unit_price": "Prix d'éxé",
        "total_amount": {"dividend": "Montant net", "tax": "Montant net"},
    },
    "type_mappings": {
        "buy": ["Achat Comptant"],
        "sell": ["Vente comptant"],
        "dividend": ["Encaissement coupons intérêt/dividende", "Encaissement coupons sur OPCVM"],
        "tax": ["TAXE TRANSAC FINAN"],
    },
    # Trades: derive the net total from gross + combined fee column (both signed).
    "formulas": {
        "total_amount": {
            "trade": [
                {"col": "Montant brut"},
                {"op": "+"},
                {"col": "Courtage/Prélèvement"},
            ],
        },
    },
    "date_formats": {"executed_at": "%d/%m/%Y"},
    "enrich_transaction_ids": "when_empty",
    "hash_columns": ["libellé", "Opération", "Date", "Qté", "Montant net"],
}


def _config(mappings: dict, delimiter: str) -> dict:
    return {"mappings": mappings, "delimiter": delimiter, "decimal_separator": "."}


@pytest.mark.skipif(not FORTUNEO_FILES, reason="no Fortuneo export in data/fortuneo/")
@pytest.mark.asyncio
async def test_fortuneo_real_file_end_to_end(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    content = FORTUNEO_FILES[0].read_bytes()  # Latin-1 encoded, ';' delimited

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=content,
        custom_schema_config=_config(FORTUNEO_MAPPINGS, ";"),
    )

    assert summary["raw_transactions_imported"] > 0
    assert summary["skipped_invalid"] == 0

    txns = list(session.exec(select(RawTransaction)).all())
    # Latin-1 decode: accented asset labels survive intact.
    assert all("�" not in (t.name or "") for t in txns)
    # No transaction-id column exists: every ID must be auto-generated.
    assert all(t.is_auto_id and t.dedup_key.startswith("auto-") for t in txns)

    # The trade formula (Montant brut + Courtage/Prélèvement) must reproduce the
    # broker's own "Montant net" on every trade row.
    trades = [t for t in txns if t.operation_type == "trade"]
    assert trades
    for trade in trades:
        raw = json.loads(trade.raw_payload)
        expected_net = parse_decimal_safe(raw["Montant net"])
        assert trade.total_amount == expected_net

    # Re-import: hash_columns-based dedup skips everything.
    summary2 = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=content,
        custom_schema_config=_config(FORTUNEO_MAPPINGS, ";"),
    )
    assert summary2["raw_transactions_imported"] == 0
    assert summary2["skipped_duplicates"] >= summary["raw_transactions_imported"]


T212_MAPPINGS = {
    "columns": {
        "operation_type": "Action",
        "executed_at": "Time",
        "isin": "ISIN",
        "ticker": "Ticker",
        "name": "Name",
        "transaction_id": "ID",
        "quantity": "No. of shares",
        "unit_price": "Price / share",
        "price_currency": "Currency (Price / share)",
        "currency": "Currency (Total)",
        "total_amount": "Total",
        "exchange_rate": "Exchange rate",
    },
    "type_mappings": {
        "buy": ["Market buy", "Limit buy"],
        "sell": ["Market sell", "Limit sell", "Stop sell"],
        "dividend": ["Dividend (Ordinary)", "Dividend (Dividend)", "Dividend (Dividends paid by us corporations)"],
        "interest": ["Interest on cash", "Lending interest"],
        "transfer_in": ["Deposit"],
        "transfer_out": ["Withdrawal"],
    },
    # Fees are spread over several columns; blanks count as zero in a sum.
    "formulas": {
        "fee_amount": [
            {"col": "Withholding tax"},
            {"op": "+"},
            {"col": "Currency conversion fee"},
            {"op": "+"},
            {"col": "French transaction tax"},
        ],
    },
    "scaling": {"unit_price": {"GBX": 0.01}, "total_amount": {"GBX": 0.01}},
    "enrich_transaction_ids": "when_empty",
}


@pytest.mark.skipif(not T212_FILES, reason="no Trading 212 2023 export in data/t212/")
@pytest.mark.asyncio
async def test_t212_real_file_end_to_end(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    content = T212_FILES[0].read_bytes()  # ',' delimited with quoted fields

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=content,
        custom_schema_config=_config(T212_MAPPINGS, ","),
    )

    assert summary["raw_transactions_imported"] > 0
    assert summary["skipped_invalid"] == 0

    txns = list(session.exec(select(RawTransaction)).all())
    # Quoted fields with embedded commas parse as single values.
    assert all('"' not in (t.name or "") for t in txns)

    # 2023 dividends ship a blank ID -> auto-generated; trades carry native EOF ids.
    dividends = [t for t in txns if t.operation_type == "dividend"]
    trades = [t for t in txns if t.operation_type == "trade"]
    assert dividends
    assert trades
    assert any(t.is_auto_id for t in dividends)
    assert any(not t.is_auto_id for t in trades)

    # The multi-column fee sum produced Fee children on withholding-taxed rows.
    fee_totals = [fee.amount for t in txns for fee in t.fees]
    assert any(amount > Decimal(0) for amount in fee_totals)

    summary2 = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=content,
        custom_schema_config=_config(T212_MAPPINGS, ","),
    )
    assert summary2["raw_transactions_imported"] == 0
