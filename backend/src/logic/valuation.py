"""Portfolio valuation math — pure, stateless Polars functions. No I/O.

Reconstructs holdings over time from allocation flows and joins persisted
daily closes to produce a market-value / net-invested time series.

Sign conventions mirror the importer's running balances exactly
(``services/import_service.py::_apply_balances``):

- trade buy       → +quantity on the asset position, -amount on portfolio cash
- trade sell      → -quantity on the asset position, +amount on portfolio cash
- stock_split     → +quantity (the extra shares delta, not a ratio)
- dividend        → +amount on portfolio cash
- cash operations → +amount on the cash position (amount sign trusted from source)

Net invested capital is the cumulative sum of *external* flows
(transfer_in / transfer_out / expense / revenue). Dividends, interest and
fees are returns/costs, not capital, so they never move the invested line.
Portfolios whose transactions contain no external cash flows at all (e.g.
trades-only imports) fall back to trade flows: buys add ``amount + fees``,
sells subtract ``amount``.

Expected input frames (all numeric columns Float64):

- ``flows_df``: position_id (i64), is_cash (bool), cash_position_id (i64 or
  null), operation_type (str), trade_side (str or null), executed_at
  (datetime), quantity, amount, fees
- ``positions_df``: position_id (i64), symbol (str or null), is_cash (bool),
  fx_rate, baseline_qty (constant holding for positions without allocations)
- ``prices_df``: symbol (str), price_date (date), close
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from datetime import date

# Operation types that represent money entering/leaving the portfolio.
_EXTERNAL_OP_TYPES = ("transfer_in", "transfer_out", "expense", "revenue")

_MONEY_QUANT = Decimal("0.01")
_SHARE_QUANT = Decimal("0.00000001")


def derive_flow_deltas(flows_df: pl.DataFrame) -> pl.DataFrame:
    """Explode allocation flows into per-position daily deltas.

    Returns columns ``position_id``, ``flow_date``, ``qty_delta`` and
    ``cost_delta`` (the position's own cost line, used as market-value
    fallback when no price exists). Trade/dividend cash side-effects are
    emitted as extra rows targeting ``cash_position_id`` when present.
    """
    is_trade = pl.col("operation_type") == "trade"
    is_buy = is_trade & (pl.col("trade_side") == "buy")
    is_sell = is_trade & (pl.col("trade_side") == "sell")
    is_dividend = pl.col("operation_type") == "dividend"

    direct = flows_df.select(
        pl.col("position_id"),
        pl.col("executed_at").dt.date().alias("flow_date"),
        pl.when(pl.col("is_cash"))
        .then(pl.col("amount"))
        .when(is_buy | (pl.col("operation_type") == "stock_split"))
        .then(pl.col("quantity"))
        .when(is_sell)
        .then(-pl.col("quantity"))
        .otherwise(pl.lit(0.0))
        .alias("qty_delta"),
        pl.when(pl.col("is_cash"))
        .then(pl.col("amount"))
        .when(is_buy)
        .then(pl.col("amount") + pl.col("fees"))
        .when(is_sell)
        .then(-pl.col("amount"))
        .otherwise(pl.lit(0.0))
        .alias("cost_delta"),
    )

    cash_side = (
        flows_df.filter(
            ~pl.col("is_cash"),
            pl.col("cash_position_id").is_not_null(),
            is_buy | is_sell | is_dividend,
        )
        .select(
            pl.col("cash_position_id").alias("position_id"),
            pl.col("executed_at").dt.date().alias("flow_date"),
            pl.when(is_buy).then(-pl.col("amount")).otherwise(pl.col("amount")).alias("qty_delta"),
        )
        .with_columns(pl.col("qty_delta").alias("cost_delta"))
    )

    return pl.concat([direct, cash_side], how="vertical_relaxed")


def derive_invested_deltas(flows_df: pl.DataFrame) -> pl.DataFrame:
    """Daily net-invested-capital deltas for the whole portfolio.

    External flows when any exist; otherwise the trades-only fallback
    (see module docstring). Returns ``flow_date``, ``invested_delta``.
    """
    external = flows_df.filter(pl.col("operation_type").is_in(_EXTERNAL_OP_TYPES))
    if external.height > 0:
        deltas = external.select(
            pl.col("executed_at").dt.date().alias("flow_date"),
            pl.col("amount").alias("invested_delta"),
        )
    else:
        is_trade = pl.col("operation_type") == "trade"
        deltas = flows_df.filter(is_trade).select(
            pl.col("executed_at").dt.date().alias("flow_date"),
            pl.when(pl.col("trade_side") == "buy")
            .then(pl.col("amount") + pl.col("fees"))
            .when(pl.col("trade_side") == "sell")
            .then(-pl.col("amount"))
            .otherwise(pl.lit(0.0))
            .alias("invested_delta"),
        )
    return deltas.group_by("flow_date").agg(pl.col("invested_delta").sum()).sort("flow_date")


def compute_current_quantities(flows_df: pl.DataFrame, positions_df: pl.DataFrame) -> dict[int, Decimal]:
    """Current quantity per position: summed flow deltas plus baseline."""
    totals: dict[int, float] = dict.fromkeys(positions_df["position_id"].to_list(), 0.0)
    if flows_df.height > 0:
        deltas = derive_flow_deltas(flows_df).group_by("position_id").agg(pl.col("qty_delta").sum())
        for pos_id, qty in deltas.iter_rows():
            if pos_id in totals:
                totals[pos_id] += qty
    for pos_id, baseline in positions_df.select("position_id", "baseline_qty").iter_rows():
        totals[pos_id] += baseline
    return {pos_id: Decimal(str(qty)).quantize(_SHARE_QUANT) for pos_id, qty in totals.items()}


def compute_valuation_series(
    flows_df: pl.DataFrame,
    positions_df: pl.DataFrame,
    prices_df: pl.DataFrame,
    start: date,
    end: date,
) -> pl.DataFrame:
    """Daily portfolio series between ``start`` and ``end`` (inclusive).

    Returns columns ``date``, ``market_value``, ``net_invested`` (Float64 —
    the service layer converts to Decimal at the boundary).

    Per position and day: quantity is the cumulative sum of its deltas plus
    baseline; value is ``quantity`` for cash, ``quantity * close * fx_rate``
    where a (forward-filled) close exists, and the position's own cumulative
    cost line before the first close / when no prices exist at all.
    """
    calendar = pl.DataFrame({"date": pl.date_range(start, end, interval="1d", eager=True)})
    if positions_df.height == 0:
        return calendar.with_columns(
            pl.lit(0.0).alias("market_value"),
            pl.lit(0.0).alias("net_invested"),
        )

    deltas = (
        derive_flow_deltas(flows_df)
        if flows_df.height > 0
        else pl.DataFrame(
            schema={"position_id": pl.Int64, "flow_date": pl.Date, "qty_delta": pl.Float64, "cost_delta": pl.Float64},
        )
    )
    daily = deltas.group_by("position_id", "flow_date").agg(
        pl.col("qty_delta").sum(),
        pl.col("cost_delta").sum(),
    )

    # Full grid (position x day). Deltas dated before ``start`` are folded
    # into the first calendar day so cumulative sums stay correct.
    daily = daily.with_columns(
        pl.when(pl.col("flow_date") < pl.lit(start)).then(pl.lit(start)).otherwise(pl.col("flow_date")).alias("date"),
    )
    daily = daily.group_by("position_id", "date").agg(pl.col("qty_delta").sum(), pl.col("cost_delta").sum())

    grid = (
        positions_df.join(calendar, how="cross")
        .join(daily, on=["position_id", "date"], how="left")
        .with_columns(pl.col("qty_delta").fill_null(0.0), pl.col("cost_delta").fill_null(0.0))
        .sort("position_id", "date")
        .with_columns(
            (pl.col("qty_delta").cum_sum().over("position_id") + pl.col("baseline_qty")).alias("qty"),
            pl.col("cost_delta").cum_sum().over("position_id").alias("cost_line"),
        )
    )

    # Closes dated before ``start`` seed the forward-fill on the first day
    # (latest pre-start close wins), mirroring the delta clamping above.
    clamped_prices = (
        prices_df.sort("price_date")
        .with_columns(
            pl.when(pl.col("price_date") < pl.lit(start))
            .then(pl.lit(start))
            .otherwise(pl.col("price_date"))
            .alias("date"),
        )
        .group_by("symbol", "date")
        .agg(pl.col("close").last())
    )
    grid = grid.join(
        clamped_prices,
        on=["symbol", "date"],
        how="left",
    ).with_columns(pl.col("close").forward_fill().over("position_id"))

    grid = grid.with_columns(
        pl.when(pl.col("is_cash"))
        .then(pl.col("qty"))
        .when(pl.col("close").is_not_null())
        .then(pl.col("qty") * pl.col("close") * pl.col("fx_rate"))
        .otherwise(pl.col("cost_line"))
        .alias("value"),
    )

    series = grid.group_by("date").agg(pl.col("value").sum().alias("market_value")).sort("date")

    invested = (
        derive_invested_deltas(flows_df)
        if flows_df.height > 0
        else pl.DataFrame(schema={"flow_date": pl.Date, "invested_delta": pl.Float64})
    )
    invested = (
        invested.with_columns(
            pl.when(pl.col("flow_date") < pl.lit(start))
            .then(pl.lit(start))
            .otherwise(pl.col("flow_date"))
            .alias("date"),
        )
        .group_by("date")
        .agg(pl.col("invested_delta").sum())
    )

    return (
        series.join(invested, on="date", how="left")
        .with_columns(pl.col("invested_delta").fill_null(0.0))
        .sort("date")
        .with_columns(pl.col("invested_delta").cum_sum().alias("net_invested"))
        .select("date", "market_value", "net_invested")
    )


def to_money(value: float | Decimal) -> Decimal:
    """Convert a computed float to a money Decimal at the service boundary."""
    return Decimal(str(value)).quantize(_MONEY_QUANT)
