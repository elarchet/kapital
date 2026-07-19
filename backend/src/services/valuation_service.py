"""Portfolio valuation service — DB orchestration around ``logic.valuation``.

Gathers a portfolio's allocation flows, lazily syncs persisted daily closes
(``price_service``), and produces the full payload for the portfolio page:
value-over-time series, per-position current figures and the asset-type
allocation rollup.

Multi-currency v1: figures are reported in the portfolio's dominant
transaction currency. When a symbol's quote currency differs from its
position's currency, the price is converted with the transaction-implied
rate (``|amount| / (quantity * unit_price)`` of the latest priced trade) and
the position is flagged ``fx_approximate``. A persisted FX-rate history is a
known follow-up.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

import polars as pl
from sqlmodel import Session, select

from src.logic.split_adjustment import compute_cost_basis
from src.logic.valuation import compute_current_quantities, compute_valuation_series, to_money
from src.models import Allocation, AssetPrice, AssetType, Portfolio, Position, RawTransaction
from src.schemas.valuation import (
    AssetTypeSlice,
    CurrentTotals,
    PortfolioValuation,
    PositionValuation,
    PriceStatus,
    ValuationPoint,
)
from src.services.financial_info import FinancialInfoService
from src.services.price_service import ensure_price_history

if TYPE_CHECKING:
    from collections.abc import Sequence

RangeKey = Literal["1m", "3m", "6m", "1y", "ytd", "all"]

_RANGE_DAYS: dict[str, int] = {"1m": 30, "3m": 91, "6m": 182, "1y": 365}
# Last close older than this many days marks a position's price as stale.
_STALE_PRICE_DAYS = 3

_financial_info_service = FinancialInfoService()


class PortfolioNotFoundError(ValueError):
    """Raised when the portfolio doesn't exist or isn't owned by the user."""


def _resolve_positions(
    db: Session,
    user_id: int,
    portfolio_id: int | Literal["unassigned"],
) -> list[Position]:
    """Active positions of the portfolio (or the 'unassigned' pseudo-portfolio)."""
    if portfolio_id == "unassigned":
        statement = (
            select(Position)
            .join(Portfolio, Position.portfolio_id == Portfolio.id)  # type: ignore[arg-type]
            .where(Portfolio.user_id == user_id, Portfolio.is_active == False, Position.is_active)  # noqa: E712
        )
        return list(db.exec(statement).all())

    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != user_id or not portfolio.is_active:
        msg = f"Portfolio {portfolio_id} not found."
        raise PortfolioNotFoundError(msg)
    return [p for p in portfolio.positions if p.is_active]


def _range_start(range_key: RangeKey, today: date, first_flow: date | None) -> date:
    earliest = first_flow or today
    if range_key == "all":
        return earliest
    start = date(today.year, 1, 1) if range_key == "ytd" else today - timedelta(days=_RANGE_DAYS[range_key])
    return max(start, earliest)


def _implied_fx_rate(rows: Sequence[tuple[Allocation, RawTransaction]], position_id: int) -> Decimal | None:
    """Transaction-implied price→transaction currency rate for a position."""
    candidates = [
        raw
        for alloc, raw in rows
        if alloc.position_id == position_id
        and raw.operation_type == "trade"
        and raw.unit_price
        and raw.quantity
        and raw.total_amount
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda r: r.executed_at)
    return abs(latest.total_amount) / (abs(latest.quantity) * abs(latest.unit_price))


def _flow_rows(
    rows: Sequence[tuple[Allocation, RawTransaction]],
    positions_by_id: dict[int, Position],
    cash_by_key: dict[tuple[int, str], int],
) -> list[dict]:
    """Build the plain rows the valuation logic consumes."""
    flow_rows: list[dict] = []
    for alloc, raw in rows:
        position = positions_by_id[alloc.position_id]
        fees_total = sum((fee.amount for fee in raw.fees), Decimal(0))
        # Fees follow the allocation proportionally to its share of the parent.
        if raw.total_amount:
            fees_total = fees_total * abs(alloc.amount) / abs(raw.total_amount)
        flow_rows.append(
            {
                "position_id": alloc.position_id,
                "is_cash": position.asset_type == AssetType.CASH,
                "cash_position_id": cash_by_key.get((position.portfolio_id, raw.currency)),
                "operation_type": raw.operation_type,
                "trade_side": str(raw.trade_side) if raw.trade_side else None,
                "executed_at": raw.executed_at,
                "quantity": float(alloc.quantity),
                "amount": float(alloc.amount),
                "fees": float(fees_total),
            },
        )
    return flow_rows


def _flows_frame(flow_rows: list[dict]) -> pl.DataFrame:
    schema = {
        "position_id": pl.Int64,
        "is_cash": pl.Boolean,
        "cash_position_id": pl.Int64,
        "operation_type": pl.String,
        "trade_side": pl.String,
        "executed_at": pl.Datetime(time_zone="UTC"),
        "quantity": pl.Float64,
        "amount": pl.Float64,
        "fees": pl.Float64,
    }
    if not flow_rows:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(flow_rows).cast(schema)  # type: ignore[arg-type]


def _positions_frame(
    positions: list[Position],
    allocated_ids: set[int],
    fx_rates: dict[int, Decimal],
) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "position_id": p.id,
                "symbol": p.ticker if p.asset_type != AssetType.CASH else None,
                "is_cash": p.asset_type == AssetType.CASH,
                "fx_rate": float(fx_rates.get(p.id, Decimal(1))),
                # Positions with no allocations (created manually) hold their
                # stored quantity as a constant over the whole range.
                "baseline_qty": float(p.quantity) if p.id not in allocated_ids else 0.0,
            }
            for p in positions
        ],
        schema={
            "position_id": pl.Int64,
            "symbol": pl.String,
            "is_cash": pl.Boolean,
            "fx_rate": pl.Float64,
            "baseline_qty": pl.Float64,
        },
    )


def _invested_by_position(rows: Sequence[tuple[Allocation, RawTransaction]]) -> dict[int, Decimal]:
    """Split-adjusted total invested per position, from the already-fetched rows."""
    by_position: dict[int, list[dict]] = {}
    for alloc, raw in rows:
        by_position.setdefault(alloc.position_id, []).append(
            {
                "operation_type": raw.operation_type,
                "trade_side": str(raw.trade_side) if raw.trade_side else None,
                "executed_at": raw.executed_at,
                "quantity": float(alloc.quantity) if alloc.quantity is not None else None,
                "unit_price": float(raw.unit_price) if raw.unit_price is not None else None,
                "total_amount": float(alloc.amount),
                "split_ratio": float(raw.split_ratio or 1.0) if raw.operation_type == "stock_split" else None,
            },
        )
    invested: dict[int, Decimal] = {}
    for position_id, op_rows in by_position.items():
        ops_df = pl.DataFrame(op_rows).with_columns(
            pl.col("executed_at").cast(pl.Datetime),
            pl.col("quantity").cast(pl.Float64),
            pl.col("unit_price").cast(pl.Float64),
            pl.col("total_amount").cast(pl.Float64),
            pl.col("split_ratio").cast(pl.Float64),
        )
        invested[position_id] = compute_cost_basis(ops_df)["total_invested"]
    return invested


def _position_valuations(
    positions: list[Position],
    quantities: dict[int, Decimal],
    latest_close: dict[str, tuple[date, Decimal]],
    fx_rates: dict[int, Decimal],
    fx_flagged: set[int],
    invested_by_position: dict[int, Decimal],
    today: date,
) -> list[PositionValuation]:
    results: list[PositionValuation] = []
    for position in positions:
        if position.id is None:
            continue
        quantity = quantities.get(position.id, Decimal(0))
        invested = invested_by_position.get(position.id, Decimal(0))

        price: Decimal | None = None
        price_date: date | None = None
        if position.asset_type == AssetType.CASH:
            status = PriceStatus.FIXED
            price = Decimal(1)
            market_value = quantity
        elif position.ticker and position.ticker in latest_close:
            price_date, close = latest_close[position.ticker]
            price = close * fx_rates.get(position.id, Decimal(1))
            status = PriceStatus.STALE if (today - price_date).days > _STALE_PRICE_DAYS else PriceStatus.OK
            market_value = quantity * price
        else:
            status = PriceStatus.COST_FALLBACK
            market_value = invested

        gain = to_money(market_value) - to_money(invested)
        results.append(
            PositionValuation(
                position_id=position.id,
                position_ids=[position.id],
                name=position.name,
                ticker=position.ticker,
                isin=position.isin,
                asset_type=position.asset_type,
                currency=position.currency,
                quantity=quantity,
                price=price.quantize(Decimal("0.00000001")) if price is not None else None,
                price_date=price_date,
                price_status=status,
                fx_approximate=position.id in fx_flagged,
                market_value=to_money(market_value),
                total_invested=to_money(invested),
                gain=gain,
                gain_pct=(gain / to_money(invested) * 100).quantize(Decimal("0.01")) if invested else None,
            ),
        )
    return results


def _asset_key(pv: PositionValuation) -> tuple:
    """Identity under which positions collapse into a single asset row."""
    if pv.asset_type == AssetType.CASH:
        return ("cash", pv.currency)
    if pv.ticker:
        return ("ticker", pv.ticker)
    if pv.isin:
        return ("isin", pv.isin)
    return ("name", pv.asset_type, pv.name or "")


def _aggregate_assets(position_vals: list[PositionValuation]) -> list[PositionValuation]:
    """Merge positions sharing an asset identity into one row per asset.

    Duplicate positions appear legitimately (several accounts, splits across
    portfolios, the 'unassigned' pool) but the repartition table shows one row
    per asset; the drilldown carries every constituent position id.
    """
    grouped: dict[tuple, list[PositionValuation]] = {}
    for pv in position_vals:
        grouped.setdefault(_asset_key(pv), []).append(pv)

    merged: list[PositionValuation] = []
    for group in grouped.values():
        first = group[0]
        if len(group) == 1:
            merged.append(first)
            continue
        market_value = sum((pv.market_value for pv in group), Decimal(0))
        invested = sum((pv.total_invested for pv in group), Decimal(0))
        gain = market_value - invested
        priced = next((pv for pv in group if pv.price is not None), first)
        merged.append(
            first.model_copy(
                update={
                    "position_ids": [pv.position_id for pv in group],
                    "name": first.name or priced.name,
                    "isin": next((pv.isin for pv in group if pv.isin), None),
                    "quantity": sum((pv.quantity for pv in group), Decimal(0)),
                    "price": priced.price,
                    "price_date": priced.price_date,
                    "price_status": priced.price_status,
                    "fx_approximate": any(pv.fx_approximate for pv in group),
                    "market_value": market_value,
                    "total_invested": invested,
                    "gain": gain,
                    "gain_pct": (gain / invested * 100).quantize(Decimal("0.01")) if invested else None,
                },
            ),
        )
    return sorted(merged, key=lambda pv: pv.market_value, reverse=True)


def _allocation_rollup(position_vals: list[PositionValuation]) -> list[AssetTypeSlice]:
    totals: dict[AssetType, Decimal] = {}
    for pv in position_vals:
        totals[pv.asset_type] = totals.get(pv.asset_type, Decimal(0)) + pv.market_value
    # Negative buckets (e.g. overdrawn cash) are excluded from percentages.
    positive_total = sum((v for v in totals.values() if v > 0), Decimal(0))
    return [
        AssetTypeSlice(
            asset_type=asset_type,
            market_value=value,
            percentage=(max(value, Decimal(0)) / positive_total * 100).quantize(Decimal("0.01"))
            if positive_total
            else Decimal(0),
        )
        for asset_type, value in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]


def _price_needs(
    positions: list[Position],
    positions_by_id: dict[int, Position],
    rows: Sequence[tuple[Allocation, RawTransaction]],
) -> dict[str, date]:
    """Earliest date daily closes are needed from, per ticker symbol."""
    needs: dict[str, date] = {}
    for alloc, raw in rows:
        position = positions_by_id[alloc.position_id]
        if position.asset_type != AssetType.CASH and position.ticker:
            executed = raw.executed_at.date()
            needs[position.ticker] = min(needs.get(position.ticker, executed), executed)
    for position in positions:
        if position.asset_type != AssetType.CASH and position.ticker and position.ticker not in needs:
            needs[position.ticker] = position.created_at.date()
    return needs


def _load_price_data(
    db: Session,
    needs: dict[str, date],
) -> tuple[Sequence[AssetPrice], dict[str, tuple[date, Decimal]], dict[str, str]]:
    """Load persisted closes plus per-symbol latest close and quote currency."""
    if not needs:
        return [], {}, {}
    price_rows: Sequence[AssetPrice] = db.exec(
        select(AssetPrice).where(AssetPrice.symbol.in_(needs)),  # type: ignore[attr-defined]
    ).all()
    latest_close: dict[str, tuple[date, Decimal]] = {}
    price_currency: dict[str, str] = {}
    for row in price_rows:
        price_currency[row.symbol] = row.currency
        current = latest_close.get(row.symbol)
        if current is None or row.price_date > current[0]:
            latest_close[row.symbol] = (row.price_date, row.close)
    return price_rows, latest_close, price_currency


def _resolve_fx(
    positions: list[Position],
    price_currency: dict[str, str],
    rows: Sequence[tuple[Allocation, RawTransaction]],
) -> tuple[dict[int, Decimal], set[int]]:
    """Transaction-implied FX for positions quoted in a different currency."""
    fx_rates: dict[int, Decimal] = {}
    fx_flagged: set[int] = set()
    for position in positions:
        if position.id is None or position.asset_type == AssetType.CASH or not position.ticker:
            continue
        quote_currency = price_currency.get(position.ticker)
        if quote_currency and quote_currency != position.currency:
            fx_flagged.add(position.id)
            implied = _implied_fx_rate(rows, position.id)
            if implied is not None:
                fx_rates[position.id] = implied
    return fx_rates, fx_flagged


def _dominant_currency(
    rows: Sequence[tuple[Allocation, RawTransaction]],
    positions: list[Position],
) -> tuple[str, bool]:
    """Most frequent transaction currency, and whether several are mixed."""
    currency_counts: dict[str, int] = {}
    for _alloc, raw in rows:
        currency_counts[raw.currency] = currency_counts.get(raw.currency, 0) + 1
    if not currency_counts:
        currency_counts = {p.currency: 1 for p in positions} or {"EUR": 1}
    dominant = max(sorted(currency_counts), key=lambda c: currency_counts[c])
    return dominant, len(currency_counts) > 1


async def get_portfolio_valuation(
    db: Session,
    *,
    user_id: int,
    portfolio_id: int | Literal["unassigned"],
    range_key: RangeKey = "1y",
) -> PortfolioValuation:
    """Assemble the full valuation payload for one portfolio."""
    positions = _resolve_positions(db, user_id, portfolio_id)
    positions_by_id = {p.id: p for p in positions if p.id is not None}

    rows: Sequence[tuple[Allocation, RawTransaction]] = []
    if positions_by_id:
        rows = db.exec(
            select(Allocation, RawTransaction)
            .join(RawTransaction, Allocation.raw_transaction_id == RawTransaction.id)  # type: ignore[arg-type]
            .where(Allocation.position_id.in_(positions_by_id), Allocation.is_active),  # type: ignore[attr-defined]
        ).all()

    cash_by_key = {
        (p.portfolio_id, p.currency): p.id for p in positions if p.asset_type == AssetType.CASH and p.id is not None
    }

    # Lazily sync daily closes for every tickered non-cash position.
    needs = _price_needs(positions, positions_by_id, rows)
    if needs:
        await ensure_price_history(db, _financial_info_service, needs)
    price_rows, latest_close, price_currency = _load_price_data(db, needs)
    fx_rates, fx_flagged = _resolve_fx(positions, price_currency, rows)

    flow_rows = _flow_rows(rows, positions_by_id, cash_by_key)
    flows_df = _flows_frame(flow_rows)
    allocated_ids = {r["position_id"] for r in flow_rows}
    positions_df = _positions_frame(positions, allocated_ids, fx_rates)
    prices_df = pl.DataFrame(
        [{"symbol": r.symbol, "price_date": r.price_date, "close": float(r.close)} for r in price_rows],
        schema={"symbol": pl.String, "price_date": pl.Date, "close": pl.Float64},
    )

    today = datetime.now(UTC).date()
    first_flow = min((r["executed_at"].date() for r in flow_rows), default=None)
    start = _range_start(range_key, today, first_flow)
    series_df = compute_valuation_series(flows_df, positions_df, prices_df, start, today)
    series = [
        ValuationPoint(date=d, market_value=to_money(mv), net_invested=to_money(ni))
        for d, mv, ni in series_df.iter_rows()
    ]

    quantities = compute_current_quantities(flows_df, positions_df)
    position_vals = _aggregate_assets(
        _position_valuations(
            positions,
            quantities,
            latest_close,
            fx_rates,
            fx_flagged,
            _invested_by_position(rows),
            today,
        ),
    )

    market_value = series[-1].market_value if series else Decimal(0)
    net_invested = series[-1].net_invested if series else Decimal(0)
    gain = market_value - net_invested
    dominant, currency_mixed = _dominant_currency(rows, positions)

    return PortfolioValuation(
        portfolio_id=portfolio_id,
        as_of=datetime.now(UTC),
        currency=dominant,
        currency_mixed=currency_mixed,
        current=CurrentTotals(
            market_value=market_value,
            net_invested=net_invested,
            gain=gain,
            gain_pct=(gain / net_invested * 100).quantize(Decimal("0.01")) if net_invested else None,
        ),
        series=series,
        positions=position_vals,
        allocation=_allocation_rollup(position_vals),
    )
