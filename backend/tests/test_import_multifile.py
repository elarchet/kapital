"""Multi-file import batches: per-file header parsing + cross-file dedup."""

from __future__ import annotations

from decimal import Decimal
from typing import cast

import pytest
from sqlmodel import select

from src.models import Portfolio, RawTransaction, User
from src.services.import_service import import_portfolio_transactions
from tests.factories import (
    PortfolioFactory,
    UserFactory,
)

CUSTOM_CONFIG = {
    "mappings": {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
        },
        "type_mappings": {
            "buy": ["BUY"],
            "dividend": ["DIV"],
        },
    },
    "delimiter": ",",
    "decimal_separator": ".",
}


@pytest.mark.asyncio
async def test_multifile_import_merges_and_dedups(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    file_a = (
        b"Type,Date,Asset,Total,Currency,Qty\n"
        b"BUY,2026-01-10 10:00:00,Apple,150.0,USD,10\n"
        b"DIV,2026-02-01 09:00:00,Apple,2.5,USD,\n"
    )
    # Second file: different column order (parsed against its own header), one
    # row duplicated from file A (same values, reordered) and one new row.
    file_b = (
        b"Date,Type,Qty,Asset,Currency,Total\n"
        b"2026-01-10 10:00:00,BUY,10,Apple,USD,150.0\n"
        b"2026-03-15 11:00:00,BUY,4,Apple,USD,80.0\n"
    )

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=[file_a, file_b],
        custom_schema_config=CUSTOM_CONFIG,
    )

    assert summary["raw_transactions_imported"] == 3
    assert summary["skipped_duplicates"] == 1

    txns = session.exec(select(RawTransaction).order_by(RawTransaction.executed_at)).all()
    assert [t.total_amount for t in txns] == [Decimal("150.0"), Decimal("2.5"), Decimal("80.0")]
    # The new row from file B parsed through its own header order.
    assert txns[-1].quantity == 4


@pytest.mark.asyncio
async def test_multifile_with_different_column_sets(session):
    """Broker period exports only carry the columns used in that period: each
    file parses against its own header, so a column missing from one file
    simply reads as empty for its rows."""
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    file_a = b"Type,Date,Asset,Total,Currency,Qty\nBUY,2026-01-10 10:00:00,Apple,150.0,USD,10\n"
    # No trades in file B's period: no Qty column; carries Notes instead.
    file_b = b"Type,Date,Asset,Notes,Total,Currency\nDIV,2026-02-01 09:00:00,Apple,Q1 payout,2.5,USD\n"

    config = {
        **CUSTOM_CONFIG,
        "mappings": {
            **CUSTOM_CONFIG["mappings"],
            "columns": {**CUSTOM_CONFIG["mappings"]["columns"], "notes": "Notes"},
        },
    }
    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=[file_a, file_b],
        custom_schema_config=config,
    )

    assert summary["raw_transactions_imported"] == 2
    assert summary["skipped_duplicates"] == 0

    txns = session.exec(select(RawTransaction).order_by(RawTransaction.executed_at)).all()
    assert txns[0].quantity == 10
    assert txns[0].notes is None  # Notes column absent from file A
    assert txns[1].quantity is None  # Qty column absent from file B
    assert txns[1].notes == "Q1 payout"


@pytest.mark.asyncio
async def test_single_bytes_content_still_supported(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(portfolio)

    csv_content = b"Type,Date,Asset,Total,Currency,Qty\nBUY,2026-01-10 10:00:00,Apple,150.0,USD,10\n"

    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=csv_content,
        custom_schema_config=CUSTOM_CONFIG,
    )

    assert summary["raw_transactions_imported"] == 1
    assert summary["skipped_duplicates"] == 0
