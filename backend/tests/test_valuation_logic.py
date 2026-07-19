"""Tests for the pure portfolio valuation math."""

from __future__ import annotations

from datetime import UTC, date, datetime

import polars as pl
import pytest

from src.logic.valuation import (
    compute_current_quantities,
    compute_valuation_series,
    derive_flow_deltas,
    derive_invested_deltas,
)

FLOW_SCHEMA = {
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
POSITION_SCHEMA = {
    "position_id": pl.Int64,
    "symbol": pl.String,
    "is_cash": pl.Boolean,
    "fx_rate": pl.Float64,
    "baseline_qty": pl.Float64,
}
PRICE_SCHEMA = {"symbol": pl.String, "price_date": pl.Date, "close": pl.Float64}


def _flow(
    position_id: int,
    day: date,
    *,
    op: str = "trade",
    side: str | None = "buy",
    qty: float = 0.0,
    amount: float = 0.0,
    fees: float = 0.0,
    is_cash: bool = False,
    cash_position_id: int | None = None,
) -> dict:
    return {
        "position_id": position_id,
        "is_cash": is_cash,
        "cash_position_id": cash_position_id,
        "operation_type": op,
        "trade_side": side,
        "executed_at": datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
        "quantity": qty,
        "amount": amount,
        "fees": fees,
    }


def _flows(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=FLOW_SCHEMA)


def _positions(rows: list[dict]) -> pl.DataFrame:
    defaults = {"symbol": None, "is_cash": False, "fx_rate": 1.0, "baseline_qty": 0.0}
    return pl.DataFrame([{**defaults, **r} for r in rows], schema=POSITION_SCHEMA)


def _prices(rows: list[tuple[str, date, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        [{"symbol": s, "price_date": d, "close": c} for s, d, c in rows],
        schema=PRICE_SCHEMA,
    )


def _series_map(df: pl.DataFrame) -> dict[date, tuple[float, float]]:
    return {d: (round(mv, 2), round(ni, 2)) for d, mv, ni in df.iter_rows()}


def test_buy_then_price_rise_tracks_market_value():
    flows = _flows([_flow(1, date(2026, 7, 1), qty=10, amount=1000)])
    positions = _positions([{"position_id": 1, "symbol": "AAA"}])
    prices = _prices([("AAA", date(2026, 7, 1), 100.0), ("AAA", date(2026, 7, 2), 110.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 2))
    series = _series_map(df)

    assert series[date(2026, 7, 1)][0] == 1000.0
    assert series[date(2026, 7, 2)][0] == 1100.0


def test_sell_to_zero_flattens_series():
    flows = _flows(
        [
            _flow(1, date(2026, 7, 1), qty=10, amount=1000),
            _flow(1, date(2026, 7, 3), side="sell", qty=10, amount=1200),
        ],
    )
    positions = _positions([{"position_id": 1, "symbol": "AAA"}])
    prices = _prices([("AAA", date(2026, 7, 1), 100.0), ("AAA", date(2026, 7, 3), 120.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 4))
    series = _series_map(df)

    assert series[date(2026, 7, 3)][0] == 0.0
    assert series[date(2026, 7, 4)][0] == 0.0


def test_weekend_forward_fills_last_close():
    flows = _flows([_flow(1, date(2026, 7, 3), qty=5, amount=500)])  # Friday
    positions = _positions([{"position_id": 1, "symbol": "AAA"}])
    prices = _prices([("AAA", date(2026, 7, 3), 100.0)])  # no weekend closes

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 3), date(2026, 7, 5))
    series = _series_map(df)

    assert series[date(2026, 7, 4)][0] == 500.0
    assert series[date(2026, 7, 5)][0] == 500.0


def test_cash_position_values_at_one():
    flows = _flows(
        [_flow(10, date(2026, 7, 1), op="transfer_in", side=None, amount=2500, is_cash=True)],
    )
    positions = _positions([{"position_id": 10, "is_cash": True}])

    df = compute_valuation_series(flows, positions, _prices([]), date(2026, 7, 1), date(2026, 7, 2))
    series = _series_map(df)

    assert series[date(2026, 7, 2)] == (2500.0, 2500.0)


def test_trade_cash_side_effect_debits_and_credits_cash():
    flows = _flows(
        [
            _flow(10, date(2026, 7, 1), op="transfer_in", side=None, amount=1000, is_cash=True),
            _flow(1, date(2026, 7, 2), qty=6, amount=600, cash_position_id=10),
            _flow(1, date(2026, 7, 4), side="sell", qty=6, amount=660, cash_position_id=10),
        ],
    )
    positions = _positions(
        [{"position_id": 1, "symbol": "AAA"}, {"position_id": 10, "is_cash": True}],
    )
    prices = _prices([("AAA", date(2026, 7, 2), 100.0), ("AAA", date(2026, 7, 4), 110.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 4))
    series = _series_map(df)

    # Buying moves value cash -> asset without changing the total.
    assert series[date(2026, 7, 1)] == (1000.0, 1000.0)
    assert series[date(2026, 7, 2)][0] == 1000.0  # 400 cash + 600 stock
    # After the sell the gain lands in cash: 400 + 660 = 1060.
    assert series[date(2026, 7, 4)][0] == 1060.0
    # Net invested only tracks the external deposit.
    assert series[date(2026, 7, 4)][1] == 1000.0


def test_dividend_credits_cash_but_not_net_invested():
    flows = _flows(
        [
            _flow(10, date(2026, 7, 1), op="transfer_in", side=None, amount=1000, is_cash=True),
            _flow(1, date(2026, 7, 2), op="dividend", side=None, amount=50, cash_position_id=10),
        ],
    )
    positions = _positions(
        [{"position_id": 1, "symbol": "AAA"}, {"position_id": 10, "is_cash": True}],
    )

    df = compute_valuation_series(flows, positions, _prices([]), date(2026, 7, 1), date(2026, 7, 2))
    series = _series_map(df)

    assert series[date(2026, 7, 2)] == (1050.0, 1000.0)


def test_trades_only_portfolio_falls_back_to_trade_flows_for_invested():
    flows = _flows(
        [
            _flow(1, date(2026, 7, 1), qty=10, amount=1000, fees=5),
            _flow(1, date(2026, 7, 3), side="sell", qty=4, amount=480),
        ],
    )
    deltas = derive_invested_deltas(flows)
    by_date = dict(deltas.iter_rows())

    assert by_date[date(2026, 7, 1)] == 1005.0
    assert by_date[date(2026, 7, 3)] == -480.0


def test_missing_price_uses_cost_line():
    flows = _flows(
        [
            _flow(1, date(2026, 7, 1), qty=10, amount=1000, fees=10),
            _flow(1, date(2026, 7, 3), side="sell", qty=5, amount=400),
        ],
    )
    positions = _positions([{"position_id": 1, "symbol": None}])

    df = compute_valuation_series(flows, positions, _prices([]), date(2026, 7, 1), date(2026, 7, 3))
    series = _series_map(df)

    assert series[date(2026, 7, 1)][0] == 1010.0
    assert series[date(2026, 7, 3)][0] == 610.0


def test_price_arriving_later_switches_from_cost_to_market():
    flows = _flows([_flow(1, date(2026, 7, 1), qty=10, amount=1000)])
    positions = _positions([{"position_id": 1, "symbol": "AAA"}])
    prices = _prices([("AAA", date(2026, 7, 3), 130.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 3))
    series = _series_map(df)

    assert series[date(2026, 7, 1)][0] == 1000.0  # cost line before first close
    assert series[date(2026, 7, 3)][0] == 1300.0


def test_stock_split_adds_quantity_delta():
    flows = _flows(
        [
            _flow(1, date(2026, 7, 1), qty=10, amount=1000),
            _flow(1, date(2026, 7, 2), op="stock_split", side=None, qty=10, amount=0),
        ],
    )
    positions = _positions([{"position_id": 1, "symbol": "AAA"}])
    prices = _prices([("AAA", date(2026, 7, 1), 100.0), ("AAA", date(2026, 7, 2), 50.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 2))
    series = _series_map(df)

    assert series[date(2026, 7, 2)][0] == 1000.0  # 20 shares @ 50


def test_flows_before_range_start_fold_into_first_day():
    flows = _flows([_flow(1, date(2026, 1, 5), qty=10, amount=1000)])
    positions = _positions([{"position_id": 1, "symbol": "AAA"}])
    prices = _prices([("AAA", date(2026, 6, 30), 150.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 2))
    series = _series_map(df)

    # Both the pre-window buy and the pre-window close must carry into day one.
    assert series[date(2026, 7, 1)][0] == 1500.0
    assert series[date(2026, 7, 2)][0] == 1500.0


def test_baseline_position_contributes_constant_quantity():
    positions = _positions([{"position_id": 1, "symbol": "AAA", "baseline_qty": 4.0}])
    prices = _prices([("AAA", date(2026, 7, 1), 25.0)])

    df = compute_valuation_series(_flows([]), positions, prices, date(2026, 7, 1), date(2026, 7, 2))
    series = _series_map(df)

    assert series[date(2026, 7, 2)][0] == 100.0


def test_fx_rate_multiplies_market_value():
    flows = _flows([_flow(1, date(2026, 7, 1), qty=10, amount=920)])
    positions = _positions([{"position_id": 1, "symbol": "AAA", "fx_rate": 0.92}])
    prices = _prices([("AAA", date(2026, 7, 1), 100.0)])

    df = compute_valuation_series(flows, positions, prices, date(2026, 7, 1), date(2026, 7, 1))
    series = _series_map(df)

    assert series[date(2026, 7, 1)][0] == 920.0


def test_empty_inputs_produce_zero_series():
    df = compute_valuation_series(_flows([]), _positions([]), _prices([]), date(2026, 7, 1), date(2026, 7, 3))
    assert df.height == 3
    assert df["market_value"].sum() == 0.0
    assert df["net_invested"].sum() == 0.0


def test_current_quantities_sum_deltas_and_baseline():
    flows = _flows(
        [
            _flow(1, date(2026, 7, 1), qty=10, amount=1000, cash_position_id=10),
            _flow(1, date(2026, 7, 2), side="sell", qty=3, amount=330, cash_position_id=10),
        ],
    )
    positions = _positions(
        [
            {"position_id": 1, "symbol": "AAA"},
            {"position_id": 10, "is_cash": True},
            {"position_id": 2, "baseline_qty": 7.5},
        ],
    )

    quantities = compute_current_quantities(flows, positions)

    assert float(quantities[1]) == 7.0
    assert float(quantities[10]) == -670.0  # -1000 + 330
    assert float(quantities[2]) == 7.5


def test_cash_side_effect_skipped_without_cash_position():
    flows = _flows([_flow(1, date(2026, 7, 1), qty=10, amount=1000, cash_position_id=None)])
    deltas = derive_flow_deltas(flows)
    assert deltas.filter(pl.col("position_id") != 1).height == 0


@pytest.mark.parametrize("op", ["transfer_out", "expense"])
def test_negative_external_flow_reduces_net_invested(op: str):
    flows = _flows(
        [
            _flow(10, date(2026, 7, 1), op="transfer_in", side=None, amount=1000, is_cash=True),
            _flow(10, date(2026, 7, 2), op=op, side=None, amount=-400, is_cash=True),
        ],
    )
    deltas = derive_invested_deltas(flows)
    by_date = dict(deltas.iter_rows())
    assert by_date[date(2026, 7, 2)] == -400.0
