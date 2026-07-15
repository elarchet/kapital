"""Integration tests for RawTransaction ingestion, idempotency, and splitting."""

from __future__ import annotations

from decimal import Decimal
from typing import cast

import pytest
from sqlmodel import select

from src.models import Allocation, AssetType, Portfolio, Position, RawTransaction, User
from src.models.allocation import AllocationMethod
from src.schemas.allocation import AllocationLine
from src.services.allocation_service import apply_split
from src.services.import_service import import_portfolio_transactions
from tests.factories import PortfolioFactory, UserFactory

_CSV = (
    "Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,"
    "Currency (Price / share),Currency (Total),Total,Exchange rate\n"
    "Market buy,2025-01-02 10:00:00,US0378331005,AAPL,Apple Inc,,TXN-1,10,100,USD,USD,1000,\n"
    "Deposit,2025-01-01 09:00:00,,,,Deposit,TXN-2,,,,EUR,500,\n"
)

_T212_CONFIG = {
    "mappings": {},
    "institution_key": "trading212",
    "delimiter": ",",
    "decimal_separator": ".",
}


@pytest.fixture
def portfolio(session):
    user = cast("User", UserFactory())
    pf = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    session.refresh(user)
    session.refresh(pf)
    return pf, user


@pytest.mark.asyncio
async def test_ingestion_creates_raw_transactions_and_default_allocations(session, portfolio):
    pf, user = portfolio
    summary = await import_portfolio_transactions(
        db=session,
        portfolio_id=pf.id,
        user_id=user.id,
        file_content=_CSV.encode(),
        custom_schema_config=_T212_CONFIG,
    )

    assert summary["raw_transactions_imported"] == 2
    assert summary["allocations_created"] == 2

    raw = session.exec(select(RawTransaction)).all()
    assert len(raw) == 2
    assert {r.native_transaction_id for r in raw} == {"TXN-1", "TXN-2"}
    assert all(r.is_auto_id is False for r in raw)  # native ids present

    allocations = session.exec(select(Allocation)).all()
    assert len(allocations) == 2
    assert all(a.is_default and a.method == AllocationMethod.PERCENTAGE for a in allocations)

    apple = session.exec(select(Position).where(Position.ticker == "AAPL")).first()
    assert apple is not None
    assert apple.quantity == Decimal(10)


@pytest.mark.asyncio
async def test_reimport_is_idempotent(session, portfolio):
    pf, user = portfolio
    first = await import_portfolio_transactions(
        db=session,
        portfolio_id=pf.id,
        user_id=user.id,
        file_content=_CSV.encode(),
        custom_schema_config=_T212_CONFIG,
    )
    assert first["raw_transactions_imported"] == 2

    second = await import_portfolio_transactions(
        db=session,
        portfolio_id=pf.id,
        user_id=user.id,
        file_content=_CSV.encode(),
        custom_schema_config=_T212_CONFIG,
    )
    assert second["raw_transactions_imported"] == 0
    assert second["skipped_duplicates"] == 2
    assert len(session.exec(select(RawTransaction)).all()) == 2


@pytest.mark.asyncio
async def test_row_without_native_id_gets_auto_key(session, portfolio):
    pf, user = portfolio
    csv_no_id = (
        "Action,Time,ISIN,Ticker,Name,Notes,ID,No. of shares,Price / share,"
        "Currency (Price / share),Currency (Total),Total,Exchange rate\n"
        "Market buy,2025-03-02 10:00:00,US0378331005,AAPL,Apple Inc,,,5,120,USD,USD,600,\n"
    )
    await import_portfolio_transactions(
        db=session,
        portfolio_id=pf.id,
        user_id=user.id,
        file_content=csv_no_id.encode(),
        custom_schema_config=_T212_CONFIG,
    )
    raw = session.exec(select(RawTransaction)).first()
    assert raw is not None
    assert raw.is_auto_id is True
    assert raw.dedup_key.startswith("auto-")


def test_apply_split_replaces_default_allocation(session, portfolio):
    pf, _ = portfolio
    raw = RawTransaction(
        operation_type="trade",
        dedup_key="TXN-SPLIT",
        native_transaction_id="TXN-SPLIT",
        financial_account_id=_make_account(session),
        quantity=Decimal(40),
        total_amount=Decimal(1000),
        currency="EUR",
        executed_at=_now(),
    )
    session.add(raw)
    pos_a = Position(portfolio_id=pf.id, asset_type=AssetType.STOCK, name="A", currency="EUR", quantity=Decimal(0))
    pos_b = Position(portfolio_id=pf.id, asset_type=AssetType.STOCK, name="B", currency="EUR", quantity=Decimal(0))
    session.add_all([pos_a, pos_b])
    session.commit()
    session.refresh(raw)
    session.refresh(pos_a)
    session.refresh(pos_b)

    user_id = pf.user_id
    lines = [
        AllocationLine(position_id=pos_a.id, method=AllocationMethod.PERCENTAGE, value=Decimal(25)),
        AllocationLine(position_id=pos_b.id, method=AllocationMethod.PERCENTAGE, value=Decimal(75)),
    ]
    allocations = apply_split(session, raw.id, lines, user_id)

    assert len(allocations) == 2
    by_pos = {a.position_id: a for a in allocations}
    assert by_pos[pos_a.id].quantity == Decimal(10)
    assert by_pos[pos_a.id].amount == Decimal(250)
    assert by_pos[pos_b.id].quantity == Decimal(30)
    assert by_pos[pos_b.id].amount == Decimal(750)


def test_apply_split_rejects_over_allocation(session, portfolio):
    pf, _ = portfolio
    raw = RawTransaction(
        operation_type="trade",
        dedup_key="TXN-OVER",
        financial_account_id=_make_account(session),
        quantity=Decimal(40),
        total_amount=Decimal(1000),
        currency="EUR",
        executed_at=_now(),
    )
    pos = Position(portfolio_id=pf.id, asset_type=AssetType.STOCK, name="A", currency="EUR", quantity=Decimal(0))
    session.add_all([raw, pos])
    session.commit()
    session.refresh(raw)
    session.refresh(pos)

    lines = [AllocationLine(position_id=pos.id, method=AllocationMethod.QUANTITY, value=Decimal(50))]
    with pytest.raises(ValueError, match="exceeds parent quantity"):
        apply_split(session, raw.id, lines, pf.user_id)


def _make_account(session) -> int:
    from tests.factories import FinancialAccountFactory  # noqa: PLC0415

    account = FinancialAccountFactory()
    session.commit()
    session.refresh(account)
    return account.id


def _now():
    from datetime import UTC, datetime  # noqa: PLC0415

    return datetime.now(UTC)
