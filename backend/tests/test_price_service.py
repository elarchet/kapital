"""Tests for the lazy price-history sync service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlmodel import select

from src.models import AssetPrice
from src.services.financial_info.models import DailyCloseSeries, HistoricalPrice
from src.services.price_service import ensure_price_history


def _point(day: date, close: str) -> HistoricalPrice:
    return HistoricalPrice(
        date=datetime(day.year, day.month, day.day, tzinfo=UTC),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=1000,
    )


def _series(symbol: str, points: list[HistoricalPrice], currency: str | None = "USD") -> DailyCloseSeries:
    return DailyCloseSeries(symbol=symbol, currency=currency, prices=points)


def _stored(session, symbol: str) -> list[AssetPrice]:
    return list(
        session.exec(select(AssetPrice).where(AssetPrice.symbol == symbol).order_by(AssetPrice.price_date)).all(),
    )


@pytest.mark.asyncio
async def test_initial_backfill_persists_all_closes(session):
    service = AsyncMock()
    service.get_daily_closes.return_value = _series(
        "AAPL",
        [_point(date(2026, 7, 14), "210.5"), _point(date(2026, 7, 15), "212.25")],
    )

    statuses = await ensure_price_history(session, service, {"AAPL": date(2026, 7, 14)})

    assert statuses == {"AAPL": "ok"}
    service.get_daily_closes.assert_awaited_once_with("AAPL", start=date(2026, 7, 14))
    rows = _stored(session, "AAPL")
    assert [(r.price_date, r.close, r.currency) for r in rows] == [
        (date(2026, 7, 14), Decimal("210.5"), "USD"),
        (date(2026, 7, 15), Decimal("212.25"), "USD"),
    ]


@pytest.mark.asyncio
async def test_incremental_fetch_starts_after_latest_stored(session):
    session.add(
        AssetPrice(symbol="AAPL", price_date=date(2026, 7, 1), close=Decimal(200), currency="USD"),
    )
    session.commit()
    service = AsyncMock()
    service.get_daily_closes.return_value = _series("AAPL", [_point(date(2026, 7, 2), "201")])

    statuses = await ensure_price_history(session, service, {"AAPL": date(2026, 1, 1)})

    assert statuses == {"AAPL": "ok"}
    service.get_daily_closes.assert_awaited_once_with("AAPL", start=date(2026, 7, 2))
    assert len(_stored(session, "AAPL")) == 2


@pytest.mark.asyncio
async def test_fresh_symbol_is_not_refetched(session):
    session.add(
        AssetPrice(symbol="AAPL", price_date=datetime.now(UTC).date(), close=Decimal(200), currency="USD"),
    )
    session.commit()
    service = AsyncMock()

    statuses = await ensure_price_history(session, service, {"AAPL": date(2026, 1, 1)})

    assert statuses == {"AAPL": "ok"}
    service.get_daily_closes.assert_not_awaited()


@pytest.mark.asyncio
async def test_rerun_is_idempotent_on_overlapping_rows(session):
    session.add(
        AssetPrice(symbol="AAPL", price_date=date(2026, 7, 1), close=Decimal(200), currency="USD"),
    )
    session.commit()
    service = AsyncMock()
    # Source returns an overlapping day plus a new one — conflict must be ignored.
    service.get_daily_closes.return_value = _series(
        "AAPL",
        [_point(date(2026, 7, 1), "999"), _point(date(2026, 7, 2), "201")],
    )

    statuses = await ensure_price_history(session, service, {"AAPL": date(2026, 1, 1)})

    assert statuses == {"AAPL": "ok"}
    rows = _stored(session, "AAPL")
    assert len(rows) == 2
    assert rows[0].close == Decimal(200)  # existing row untouched


@pytest.mark.asyncio
async def test_source_failure_reports_failed_without_raising(session):
    service = AsyncMock()
    service.get_daily_closes.side_effect = RuntimeError("yfinance down")

    statuses = await ensure_price_history(session, service, {"AAPL": date(2026, 1, 1)})

    assert statuses == {"AAPL": "failed"}
    assert _stored(session, "AAPL") == []


@pytest.mark.asyncio
async def test_empty_backfill_reports_empty(session):
    service = AsyncMock()
    service.get_daily_closes.return_value = _series("BOGUS", [], currency=None)

    statuses = await ensure_price_history(session, service, {"BOGUS": date(2026, 1, 1)})

    assert statuses == {"BOGUS": "empty"}
    assert _stored(session, "BOGUS") == []


@pytest.mark.asyncio
async def test_mixed_symbols_one_failure_does_not_block_others(session):
    service = AsyncMock()

    async def _closes(symbol: str, **_kwargs: object) -> DailyCloseSeries:
        if symbol == "BAD":
            raise RuntimeError("boom")
        return _series(symbol, [_point(date(2026, 7, 15), "50")], currency="EUR")

    service.get_daily_closes.side_effect = _closes

    statuses = await ensure_price_history(
        session,
        service,
        {"BAD": date(2026, 1, 1), "MC.PA": date(2026, 1, 1)},
    )

    assert statuses == {"BAD": "failed", "MC.PA": "ok"}
    assert len(_stored(session, "MC.PA")) == 1
