"""RawTransaction + Allocation router.

Raw transactions are the immutable ingested records; allocations are the
user-defined splits that route each transaction to one or more positions.
Ownership is always resolved through allocation -> position -> portfolio -> user.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session, select

from src.auth import get_current_user
from src.database import get_session
from src.models.allocation import Allocation
from src.models.portfolio import Portfolio
from src.models.position import Position
from src.models.raw_transaction import RawTransaction
from src.models.user import User
from src.schemas.allocation import AllocationRead, AllocationRecombineRequest, AllocationSplitRequest
from src.schemas.raw_transaction import RawTransactionRead
from src.services.allocation_service import apply_split, recombine

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    return current_user.id


def _get_owned_transaction(db: Session, transaction_id: int, user_id: int) -> RawTransaction:
    """Return a raw transaction the user owns via any of its allocations."""
    statement = (
        select(RawTransaction)
        .join(Allocation, Allocation.raw_transaction_id == RawTransaction.id)  # type: ignore[arg-type]
        .join(Position, Allocation.position_id == Position.id)  # type: ignore[arg-type]
        .join(Portfolio, Position.portfolio_id == Portfolio.id)  # type: ignore[arg-type]
        .where(RawTransaction.id == transaction_id, Portfolio.user_id == user_id)
    )
    transaction = db.exec(statement).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    return transaction


@router.get("/", response_model=list[RawTransactionRead])
def read_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    position_id: Annotated[list[int] | None, Query(description="Filter by position IDs (repeatable)")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[RawTransaction]:
    """List raw transactions the user owns, optionally scoped to positions."""
    user_id = _require_user_id(current_user)
    statement = (
        select(RawTransaction)
        .join(Allocation, Allocation.raw_transaction_id == RawTransaction.id)  # type: ignore[arg-type]
        .join(Position, Allocation.position_id == Position.id)  # type: ignore[arg-type]
        .join(Portfolio, Position.portfolio_id == Portfolio.id)  # type: ignore[arg-type]
        .where(Portfolio.user_id == user_id)
    )
    if position_id:
        statement = statement.where(Allocation.position_id.in_(position_id))  # type: ignore[attr-defined]
    statement = statement.distinct().offset(skip).limit(limit)
    return list(db.exec(statement).all())


@router.get("/{transaction_id}", response_model=RawTransactionRead)
def read_transaction(
    transaction_id: Annotated[int, Path(description="The raw transaction ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> RawTransaction:
    """Retrieve a single raw transaction owned by the user."""
    return _get_owned_transaction(db, transaction_id, _require_user_id(current_user))


@router.delete("/{transaction_id}", response_model=RawTransactionRead)
def delete_transaction(
    transaction_id: Annotated[int, Path(description="The raw transaction ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> RawTransaction:
    """Delete a raw transaction and its allocations/fees (cascade)."""
    transaction = _get_owned_transaction(db, transaction_id, _require_user_id(current_user))
    db.delete(transaction)
    db.commit()
    return transaction


@router.get("/{transaction_id}/allocations", response_model=list[AllocationRead])
def read_allocations(
    transaction_id: Annotated[int, Path(description="The raw transaction ID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> list[Allocation]:
    """List the allocations (splits) of a raw transaction."""
    _get_owned_transaction(db, transaction_id, _require_user_id(current_user))
    statement = select(Allocation).where(
        Allocation.raw_transaction_id == transaction_id,
        Allocation.is_active,
    )
    return list(db.exec(statement).all())


@router.post(
    "/{transaction_id}/allocations",
    response_model=list[AllocationRead],
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Invalid split (over-allocation / unowned position)."}},
)
def split_transaction(
    transaction_id: Annotated[int, Path(description="The raw transaction ID")],
    split_in: AllocationSplitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> list[Allocation]:
    """Replace a transaction's allocations with a new split across positions/portfolios."""
    user_id = _require_user_id(current_user)
    _get_owned_transaction(db, transaction_id, user_id)
    try:
        return apply_split(db, transaction_id, split_in.lines, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{transaction_id}/allocations/recombine",
    response_model=list[AllocationRead],
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Invalid target position."}},
)
def recombine_transaction(
    transaction_id: Annotated[int, Path(description="The raw transaction ID")],
    recombine_in: AllocationRecombineRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> list[Allocation]:
    """Collapse a transaction's splits back into a single 100% allocation."""
    user_id = _require_user_id(current_user)
    _get_owned_transaction(db, transaction_id, user_id)
    try:
        return recombine(db, transaction_id, recombine_in.position_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
