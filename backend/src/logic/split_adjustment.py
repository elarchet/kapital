"""Split adjustment logic — pure, stateless Polars functions.

No database calls. Takes a Polars DataFrame of operations for one or more positions
and returns it enriched with split-adjustment columns.

Tax-forward design note:
    The returned DataFrame includes one row per trade with its ``split_factor``.
    A future FIFO tax lot module can consume these adjusted rows directly,
    iterating ``executed_at`` ascending to match lots against disposals.
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_split_adjusted_operations(ops_df: pl.DataFrame) -> pl.DataFrame:
    """Add split-adjustment columns to an operations DataFrame.

    The DataFrame must contain **all** operations for a single position
    (or be pre-grouped by position_id if called across positions).

    Required input columns:
        - ``operation_type`` (str): "trade", "stock_split", etc.
        - ``trade_side`` (str | None): "buy" / "sell" for trades
        - ``executed_at`` (datetime): wall-clock execution time
        - ``quantity`` (Decimal-compatible numeric): raw broker quantity
        - ``unit_price`` (Decimal-compatible numeric | None): raw broker price
        - ``total_amount`` (Decimal-compatible numeric): real cash value (NEVER adjusted)

    Added output columns:
        - ``split_factor`` (Float64): cumulative ratio to apply to this row.
          = PRODUCT of split_ratio for all stock_split rows with
          executed_at > this row's executed_at.
          Defaults to 1.0 if no subsequent splits exist.
        - ``adj_quantity`` (Float64): quantity * split_factor
        - ``adj_unit_price`` (Float64 | None): unit_price / split_factor
          (None preserved as None)

    Key invariant:
        ``total_amount`` is NEVER modified — it represents real cash flow and is
        split-invariant by definition.
    """
    if ops_df.is_empty():
        return ops_df.with_columns(
            [
                pl.lit(1.0).alias("split_factor"),
                pl.col("quantity").cast(pl.Float64).alias("adj_quantity"),
                pl.col("unit_price").cast(pl.Float64).alias("adj_unit_price"),
            ],
        )

    # Extract split events for this position
    splits_df = (
        ops_df.filter(pl.col("operation_type") == "stock_split")
        .select(["executed_at", "split_ratio"])
        .with_columns(pl.col("split_ratio").cast(pl.Float64))
        .sort("executed_at")
    )

    if splits_df.is_empty():
        # No splits: factor = 1.0, adj = raw
        return ops_df.with_columns(
            [
                pl.lit(1.0).alias("split_factor"),
                pl.col("quantity").cast(pl.Float64).alias("adj_quantity"),
                pl.col("unit_price").cast(pl.Float64).alias("adj_unit_price"),
            ],
        )

    # Compute cumulative product of split ratios per trade row.
    # For each trade at time T, the factor is the product of all splits at time > T.
    # We do this with a cross-join (small splits_df x ops_df) then aggregate.
    split_times = splits_df["executed_at"].to_list()
    split_ratios = splits_df["split_ratio"].to_list()

    def _compute_factor(trade_time: pl.Series) -> pl.Series:
        """Compute cumulative split factor for each row's executed_at timestamp."""
        factors = []
        for t in trade_time:
            factor = 1.0
            for i, split_t in enumerate(split_times):
                if split_t > t:
                    ratio = split_ratios[i]
                    if ratio and ratio != 0:
                        factor *= float(ratio)
            factors.append(factor)
        return pl.Series("split_factor", factors, dtype=pl.Float64)

    result = ops_df.with_columns(
        _compute_factor(ops_df["executed_at"]).alias("split_factor"),
    ).with_columns(
        [
            (pl.col("quantity").cast(pl.Float64) * pl.col("split_factor")).alias("adj_quantity"),
            pl.when(pl.col("unit_price").is_not_null())
            .then(pl.col("unit_price").cast(pl.Float64) / pl.col("split_factor"))
            .otherwise(pl.lit(None, dtype=pl.Float64))
            .alias("adj_unit_price"),
        ],
    )

    return result


def compute_cost_basis(ops_df: pl.DataFrame) -> dict[str, Decimal]:
    """Compute split-adjusted cost basis metrics for a single position.

    Runs ``compute_split_adjusted_operations`` internally.

    Returns:
        dict with keys:
          - ``avg_cost_basis``: Decimal — split-adjusted weighted avg cost per share
          - ``total_invested``: Decimal — total cash deployed in BUY trades (split-invariant)
          - ``total_shares``: Decimal — total split-adjusted shares from BUY trades
    """
    if ops_df.is_empty():
        return {
            "avg_cost_basis": Decimal(0),
            "total_invested": Decimal(0),
            "total_shares": Decimal(0),
        }

    adjusted = compute_split_adjusted_operations(ops_df)

    buy_trades = adjusted.filter(
        (pl.col("operation_type") == "trade") & (pl.col("trade_side") == "buy"),
    )

    if buy_trades.is_empty():
        return {
            "avg_cost_basis": Decimal(0),
            "total_invested": Decimal(0),
            "total_shares": Decimal(0),
        }

    total_invested = Decimal(
        str(
            buy_trades.select(pl.col("total_amount").cast(pl.Float64).sum()).item(),
        ),
    )
    total_shares = Decimal(
        str(
            buy_trades.select(pl.col("adj_quantity").sum()).item(),
        ),
    )

    avg_cost_basis = total_invested / total_shares if total_shares != Decimal(0) else Decimal(0)

    return {
        "avg_cost_basis": avg_cost_basis.quantize(Decimal("0.00000001")),
        "total_invested": total_invested.quantize(Decimal("0.01")),
        "total_shares": total_shares.quantize(Decimal("0.00000001")),
    }
