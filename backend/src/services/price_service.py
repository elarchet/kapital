"""Price history sync — lazily persist daily closes from yfinance.

Called on demand by the valuation service: the first request for a symbol
backfills its whole history from the asset's earliest transaction date; later
requests only top up the missing recent days (weekends/holidays return empty
frames and cost a single cheap call). A yfinance outage never fails the
caller — affected symbols simply report a non-ok status and valuation falls
back to cost for them.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, func, select

from src.models import AssetPrice

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.services.financial_info import FinancialInfoService

# Prices older than this many days trigger an incremental top-up fetch.
_STALE_AFTER_DAYS = 1


def _today() -> date:
    return datetime.now(UTC).date()


async def ensure_price_history(
    db: Session,
    financial_info_service: FinancialInfoService,
    needs: Mapping[str, date],
) -> dict[str, str]:
    """Make sure daily closes exist for each symbol from its needed start date.

    Args:
        db: Database session.
        financial_info_service: yfinance wrapper used for fetches.
        needs: Maps ticker symbol -> earliest date history is needed from
            (typically the asset's first transaction date).

    Returns:
        Per-symbol status: ``"ok"`` (fresh or topped up), ``"empty"`` (source
        returned no rows) or ``"failed"`` (source errored). Never raises for
        source failures.
    """
    statuses: dict[str, str] = {}
    today = _today()
    rows_to_insert: list[dict] = []

    for symbol, needed_start in needs.items():
        latest = db.exec(
            select(func.max(AssetPrice.price_date)).where(AssetPrice.symbol == symbol),
        ).one()

        if latest is None:
            fetch_start = needed_start
        elif today - latest > timedelta(days=_STALE_AFTER_DAYS):
            fetch_start = latest + timedelta(days=1)
        else:
            statuses[symbol] = "ok"
            continue

        try:
            series = await financial_info_service.get_daily_closes(symbol, start=fetch_start)
        except Exception:  # noqa: BLE001 — source outage must not break valuation
            statuses[symbol] = "failed"
            continue

        if not series.prices:
            # No trading days in the window (weekend/holiday) is normal when
            # topping up; an empty full backfill means the symbol is unknown.
            statuses[symbol] = "ok" if latest is not None else "empty"
            continue

        currency = series.currency or "EUR"
        rows_to_insert.extend(
            {
                "symbol": symbol,
                "price_date": point.date.date(),
                "close": point.close,
                "currency": currency,
                "source": "yfinance",
            }
            for point in series.prices
        )
        statuses[symbol] = "ok"

    if rows_to_insert:
        try:
            db.execute(
                pg_insert(AssetPrice.__table__)
                .values(rows_to_insert)
                .on_conflict_do_nothing(constraint="uq_asset_price_symbol_date"),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    return statuses
