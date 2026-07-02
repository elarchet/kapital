"""Cost basis service — fetches operations from DB and delegates to logic layer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import polars as pl
from sqlmodel import select

from src.logic.split_adjustment import compute_cost_basis
from src.models.operation import Operation, StockSplitOperation

if TYPE_CHECKING:
    from datetime import datetime

    from sqlmodel import Session


@dataclass(frozen=True)
class SplitEvent:
    """Audit record for a single split event."""

    executed_at: datetime
    split_ratio: Decimal
    pre_split_quantity: Decimal | None
    post_split_quantity: Decimal | None


@dataclass(frozen=True)
class CostBasisResult:
    """Split-adjusted cost basis for a single position."""

    position_id: int
    avg_cost_basis: Decimal
    total_invested: Decimal
    total_shares: Decimal
    split_events: list[SplitEvent]


def get_position_cost_basis(db: Session, position_id: int) -> CostBasisResult:
    """Compute split-adjusted cost basis for a position.

    Fetches all operations for the position, builds a Polars DataFrame,
    and delegates math to the pure ``compute_cost_basis()`` logic function.

    Design note (tax-forward):
        The underlying ``compute_split_adjusted_operations()`` returns one row
        per trade with its ``split_factor``. A future FIFO tax-lot service can
        consume that adjusted DataFrame directly to match disposals against
        acquisition lots in chronological order.
    """
    ops = db.exec(
        select(Operation).where(Operation.position_id == position_id),
    ).all()

    if not ops:
        return CostBasisResult(
            position_id=position_id,
            avg_cost_basis=Decimal(0),
            total_invested=Decimal(0),
            total_shares=Decimal(0),
            split_events=[],
        )

    # Build Polars DataFrame from ORM objects (no N+1 — single query above)
    rows = [
        {
            "operation_type": op.operation_type,
            "trade_side": str(op.trade_side) if op.trade_side else None,
            "executed_at": op.executed_at,
            "quantity": float(op.quantity) if op.quantity is not None else None,
            "unit_price": float(op.unit_price) if op.unit_price is not None else None,
            "total_amount": float(op.total_amount),
            "split_ratio": float(getattr(op, "split_ratio", None) or 1.0)
            if op.operation_type == "stock_split"
            else None,
        }
        for op in ops
    ]

    ops_df = pl.DataFrame(rows).with_columns(
        [
            pl.col("executed_at").cast(pl.Datetime),
            pl.col("quantity").cast(pl.Float64),
            pl.col("unit_price").cast(pl.Float64),
            pl.col("total_amount").cast(pl.Float64),
            pl.col("split_ratio").cast(pl.Float64),
        ],
    )

    metrics = compute_cost_basis(ops_df)

    # Collect split events for audit display
    split_events: list[SplitEvent] = []
    for op in ops:
        if isinstance(op, StockSplitOperation) and op.split_ratio:
            pre_qty = getattr(op, "pre_split_quantity", None)
            post_qty = pre_qty * op.split_ratio if pre_qty and op.split_ratio else None
            split_events.append(
                SplitEvent(
                    executed_at=op.executed_at,
                    split_ratio=op.split_ratio,
                    pre_split_quantity=pre_qty,
                    post_split_quantity=post_qty,
                ),
            )

    split_events.sort(key=lambda e: e.executed_at)

    return CostBasisResult(
        position_id=position_id,
        avg_cost_basis=metrics["avg_cost_basis"],
        total_invested=metrics["total_invested"],
        total_shares=metrics["total_shares"],
        split_events=split_events,
    )
