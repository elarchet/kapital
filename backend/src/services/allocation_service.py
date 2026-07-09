"""Allocation service — create default allocations and apply user splits.

A ``RawTransaction`` is immutable; user segmentation happens by (re)writing its
``Allocation`` child rows. On import every transaction receives a single 100%
default allocation so positions stay populated; users may later replace it with
an arbitrary set of splits across positions.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlmodel import Session, select

from src.logic.allocation_split import resolve_allocation, validate_split_totals
from src.models import Allocation, AllocationMethod, Portfolio, Position, RawTransaction

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.schemas.allocation import AllocationLine


def make_default_allocation(
    raw_txn: RawTransaction,
    position: Position,
    op_info: Mapping[str, Any],
) -> Allocation:
    """Build the immutable 100% default allocation created at ingestion time."""
    quantity = op_info.get("quantity") or Decimal(0)
    amount = op_info.get("total_amount")
    return Allocation(
        raw_transaction=raw_txn,
        position=position,
        method=AllocationMethod.PERCENTAGE,
        value=Decimal(100),
        quantity=quantity,
        amount=amount if amount is not None else Decimal(0),
        currency=op_info.get("currency") or "EUR",
        is_default=True,
    )


def apply_split(
    db: Session,
    raw_transaction_id: int,
    lines: Sequence[AllocationLine],
    user_id: int,
) -> list[Allocation]:
    """Replace a raw transaction's allocations with the provided split lines.

    Validates that the target positions belong to the current user and that the
    resolved splits never over-allocate the parent transaction.

    Raises:
        ValueError: If the transaction/positions are not found or the split is
            invalid (unowned position, over-allocation).
    """
    raw_txn = db.get(RawTransaction, raw_transaction_id)
    if raw_txn is None:
        msg = f"RawTransaction {raw_transaction_id} not found."
        raise ValueError(msg)

    position_ids = [line.position_id for line in lines]
    owned = db.exec(
        select(Position.id)
        .join(Portfolio, Position.portfolio_id == Portfolio.id)  # type: ignore[arg-type]
        .where(
            Position.id.in_(position_ids),  # type: ignore[attr-defined]
            Portfolio.user_id == user_id,
            Position.is_active,
        ),
    ).all()
    owned_ids = set(owned)
    missing = set(position_ids) - owned_ids
    if missing:
        msg = f"Positions not found or not owned by user: {sorted(missing)}"
        raise ValueError(msg)

    resolved = [
        resolve_allocation(
            line.method,
            line.value,
            parent_quantity=raw_txn.quantity,
            parent_amount=raw_txn.total_amount,
        )
        for line in lines
    ]
    validate_split_totals(
        resolved,
        parent_quantity=raw_txn.quantity,
        parent_amount=raw_txn.total_amount,
    )

    # Remove previous allocations (default or prior split) and write the new set.
    for existing in list(raw_txn.allocations):
        db.delete(existing)

    allocations = [
        Allocation(
            raw_transaction_id=raw_transaction_id,
            position_id=line.position_id,
            method=line.method,
            value=line.value,
            quantity=quantity,
            amount=amount,
            currency=raw_txn.currency,
            is_default=False,
            notes=line.notes,
        )
        for line, (quantity, amount) in zip(lines, resolved, strict=True)
    ]
    db.add_all(allocations)
    db.commit()
    for allocation in allocations:
        db.refresh(allocation)
    return allocations
