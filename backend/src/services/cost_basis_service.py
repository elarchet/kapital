"""Cost basis service — fetches operations from DB and delegates to logic layer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import polars as pl
from sqlmodel import select

from src.logic.split_adjustment import compute_cost_basis
from src.models.allocation import Allocation
from src.models.raw_transaction import RawTransaction

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

    Fetches every allocation routed to the position joined to its parent raw
    transaction (allocated ``quantity``/``amount`` come from the allocation;
    financial attributes come from the raw transaction), builds a Polars
    DataFrame, and delegates the math to ``compute_cost_basis()``.
    """
    rows_db = db.exec(
        select(Allocation, RawTransaction)
        .join(RawTransaction, Allocation.raw_transaction_id == RawTransaction.id)  # type: ignore[arg-type]
        .where(Allocation.position_id == position_id, Allocation.is_active),
    ).all()

    if not rows_db:
        return CostBasisResult(
            position_id=position_id,
            avg_cost_basis=Decimal(0),
            total_invested=Decimal(0),
            total_shares=Decimal(0),
            split_events=[],
        )

    # Build Polars DataFrame from (Allocation, RawTransaction) pairs — single query.
    rows = [
        {
            "operation_type": raw.operation_type,
            "trade_side": str(raw.trade_side) if raw.trade_side else None,
            "executed_at": raw.executed_at,
            "quantity": float(alloc.quantity) if alloc.quantity is not None else None,
            "unit_price": float(raw.unit_price) if raw.unit_price is not None else None,
            "total_amount": float(alloc.amount),
            "split_ratio": float(raw.split_ratio or 1.0) if raw.operation_type == "stock_split" else None,
        }
        for alloc, raw in rows_db
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
    for _alloc, raw in rows_db:
        if raw.operation_type == "stock_split" and raw.split_ratio:
            pre_qty = raw.pre_split_quantity
            post_qty = pre_qty * raw.split_ratio if pre_qty and raw.split_ratio else None
            split_events.append(
                SplitEvent(
                    executed_at=raw.executed_at,
                    split_ratio=raw.split_ratio,
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
