"""Allocation service — create default allocations and apply user splits.

A ``RawTransaction`` is immutable; user segmentation happens by (re)writing its
``Allocation`` child rows. On import every transaction receives a single 100%
default allocation so positions stay populated; users may later replace it with
an arbitrary set of splits across positions — or across portfolios, in which
case the matching position in the target portfolio is found or created.

Known v1 limitation: trades also debit/credit a *cash* position at import and
that cash flow is not represented by allocations, so splitting a trade across
portfolios moves the asset but not its cash impact. Cash positions are
therefore never recomputed from allocations here.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlmodel import Session, select

from src.logic.allocation_split import resolve_allocation, validate_split_totals
from src.models import Allocation, AllocationMethod, AssetType, Portfolio, Position, RawTransaction
from src.schemas.allocation import AllocationLine

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence


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


def _source_position(db: Session, raw_txn: RawTransaction) -> Position | None:
    """The position the transaction currently routes to (asset identity template)."""
    current = sorted(raw_txn.allocations, key=lambda a: (not a.is_default, a.id or 0))
    for allocation in current:
        position = db.get(Position, allocation.position_id)
        if position is not None:
            return position
    return None


def _find_or_create_position(
    db: Session,
    portfolio: Portfolio,
    template: Position,
    raw_txn: RawTransaction,
) -> Position:
    """Locate the portfolio's position matching the transaction's asset, or create it."""
    ticker = raw_txn.ticker or template.ticker
    isin = raw_txn.isin or template.isin
    for position in portfolio.positions:
        if not position.is_active or position.asset_type != template.asset_type:
            continue
        if (ticker and position.ticker == ticker) or (isin and position.isin == isin):
            return position
        if not ticker and not isin and position.name == template.name:
            return position
    created = Position(
        asset_type=template.asset_type,
        ticker=ticker,
        name=raw_txn.name or template.name,
        isin=isin,
        quantity=Decimal(0),
        currency=template.currency,
        portfolio_id=portfolio.id,  # type: ignore[arg-type]
    )
    db.add(created)
    db.flush()  # assign an id so allocations can reference it pre-commit
    return created


def _resolve_target_position_ids(
    db: Session,
    raw_txn: RawTransaction,
    lines: Sequence[AllocationLine],
    user_id: int,
) -> list[int]:
    """Map each line to a concrete owned position id, creating positions as needed."""
    direct_ids = [line.position_id for line in lines if line.position_id is not None]
    if direct_ids:
        owned = set(
            db.exec(
                select(Position.id)
                .join(Portfolio, Position.portfolio_id == Portfolio.id)  # type: ignore[arg-type]
                .where(
                    Position.id.in_(direct_ids),  # type: ignore[attr-defined]
                    Portfolio.user_id == user_id,
                    Position.is_active,
                ),
            ).all(),
        )
        missing = set(direct_ids) - owned
        if missing:
            msg = f"Positions not found or not owned by user: {sorted(missing)}"
            raise ValueError(msg)

    template: Position | None = None
    portfolio_cache: dict[int, Position] = {}
    resolved: list[int] = []
    for line in lines:
        if line.position_id is not None:
            resolved.append(line.position_id)
            continue
        if line.portfolio_id is None:  # schema validator guarantees one target
            msg = "Allocation line has neither position_id nor portfolio_id."
            raise ValueError(msg)
        if line.portfolio_id in portfolio_cache:
            resolved.append(portfolio_cache[line.portfolio_id].id)  # type: ignore[arg-type]
            continue
        portfolio = db.get(Portfolio, line.portfolio_id)
        if portfolio is None or portfolio.user_id != user_id or not portfolio.is_active:
            msg = f"Portfolio {line.portfolio_id} not found or not owned by user."
            raise ValueError(msg)
        if template is None:
            template = _source_position(db, raw_txn)
        if template is None:
            msg = "Transaction has no existing allocation to derive the asset from."
            raise ValueError(msg)
        target = _find_or_create_position(db, portfolio, template, raw_txn)
        portfolio_cache[line.portfolio_id] = target
        resolved.append(target.id)  # type: ignore[arg-type]
    return resolved


def recompute_position_quantities(db: Session, position_ids: Iterable[int]) -> None:
    """Rebuild non-cash position quantities from their active allocations.

    Signing mirrors the importer's running balances (buy +qty, sell -qty,
    stock_split +qty). Cash positions are skipped — their balances include
    trade side-effects that allocations don't carry. Zero-quantity positions
    are kept so a recombine can restore them losslessly.
    """
    ids = [pid for pid in set(position_ids) if pid is not None]
    if not ids:
        return
    positions = {p.id: p for p in db.exec(select(Position).where(Position.id.in_(ids))).all()}  # type: ignore[attr-defined]
    rows = db.exec(
        select(Allocation, RawTransaction)
        .join(RawTransaction, Allocation.raw_transaction_id == RawTransaction.id)  # type: ignore[arg-type]
        .where(Allocation.position_id.in_(ids), Allocation.is_active),  # type: ignore[attr-defined]
    ).all()

    totals: dict[int, Decimal] = dict.fromkeys(positions, Decimal(0))
    for alloc, raw in rows:
        side = str(raw.trade_side) if raw.trade_side else None
        if raw.operation_type == "trade" and side == "buy":
            totals[alloc.position_id] += alloc.quantity
        elif raw.operation_type == "trade" and side == "sell":
            totals[alloc.position_id] -= alloc.quantity
        elif raw.operation_type == "stock_split":
            totals[alloc.position_id] += alloc.quantity

    for position_id, quantity in totals.items():
        position = positions[position_id]
        if position.asset_type == AssetType.CASH:
            continue
        position.quantity = quantity
        db.add(position)


def apply_split(
    db: Session,
    raw_transaction_id: int,
    lines: Sequence[AllocationLine],
    user_id: int,
) -> list[Allocation]:
    """Replace a raw transaction's allocations with the provided split lines.

    Lines may target positions directly or via a portfolio (find-or-create).
    The resolved splits must fully cover the parent transaction; affected
    non-cash positions get their quantities recomputed from allocations.

    Raises:
        ValueError: If the transaction/targets are not found or the split is
            invalid (unowned target, over- or under-allocation).
    """
    raw_txn = db.get(RawTransaction, raw_transaction_id)
    if raw_txn is None:
        msg = f"RawTransaction {raw_transaction_id} not found."
        raise ValueError(msg)

    previous_position_ids = [allocation.position_id for allocation in raw_txn.allocations]
    target_position_ids = _resolve_target_position_ids(db, raw_txn, lines, user_id)

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
        require_full=True,
    )

    # Remove previous allocations (default or prior split) and write the new set.
    for existing in list(raw_txn.allocations):
        db.delete(existing)

    allocations = [
        Allocation(
            raw_transaction_id=raw_transaction_id,
            position_id=position_id,
            method=line.method,
            value=line.value,
            quantity=quantity,
            amount=amount,
            currency=raw_txn.currency,
            is_default=False,
            notes=line.notes,
        )
        for line, position_id, (quantity, amount) in zip(lines, target_position_ids, resolved, strict=True)
    ]
    db.add_all(allocations)
    db.flush()
    recompute_position_quantities(db, [*previous_position_ids, *target_position_ids])
    db.commit()
    for allocation in allocations:
        db.refresh(allocation)
    return allocations


def recombine(
    db: Session,
    raw_transaction_id: int,
    position_id: int,
    user_id: int,
) -> list[Allocation]:
    """Collapse a transaction's splits back into a single 100% allocation.

    Lossless by construction: dedup identity lives on the immutable
    ``RawTransaction`` and quantities are recomputed from allocations.
    """
    line = AllocationLine(position_id=position_id, method=AllocationMethod.PERCENTAGE, value=Decimal(100))
    return apply_split(db, raw_transaction_id, [line], user_id)
