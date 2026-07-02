from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session, select

from src.auth import get_current_user
from src.database import get_session
from src.models.fee import Fee
from src.models.financial_account import FinancialAccount
from src.models.operation import OPERATION_TYPE_MAP, Operation
from src.models.portfolio import Portfolio
from src.models.position import Position
from src.models.user import User
from src.schemas.operation import OperationCreate, OperationRead, OperationUpdate

router = APIRouter(prefix="/operations", tags=["operations"])


@router.post(
    "/",
    response_model=OperationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Linked position or financial account not found."},
    },
)
def create_operation(
    operation_in: OperationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Operation:
    """Create a new operation, verifying position ownership and financial account existence."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    # 1. Validate position ownership
    position = db.exec(
        select(Position)
        .join(Portfolio)
        .where(
            Position.id == operation_in.position_id,
            Portfolio.user_id == current_user.id,
            Position.is_active,
        ),
    ).first()
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked position not found or not owned by user.",
        )

    # 2. Validate financial account existence
    account = db.exec(
        select(FinancialAccount).where(
            FinancialAccount.id == operation_in.financial_account_id,
            FinancialAccount.is_active == True,  # noqa: E712
        ),
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked financial account not found.",
        )

    op_type = operation_in.operation_type
    model_cls = OPERATION_TYPE_MAP.get(op_type)
    if not model_cls:
        raise HTTPException(status_code=400, detail=f"Unknown operation type: {op_type}")

    obj_data = operation_in.model_dump()
    fees_data = obj_data.pop("fees", None)

    mapper = model_cls.__mapper__
    valid_keys = set(mapper.attrs.keys())
    filtered_data = {k: v for k, v in obj_data.items() if k in valid_keys or hasattr(model_cls, k)}

    db_obj = model_cls(**filtered_data)
    if fees_data:
        db_obj.fees = [Fee(**fee) for fee in fees_data]

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get(
    "/",
    response_model=list[OperationRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Filtered position not found or not owned by user."},
    },
)
def read_operations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    position_id: Annotated[int | None, Query(description="Filter operations by a specific position ID")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of operations to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of operations to return")] = 100,
) -> list[Operation]:
    """Retrieve active operations, optionally filtered by position_id."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    if position_id is not None:
        position = db.exec(
            select(Position)
            .join(Portfolio)
            .where(Position.id == position_id, Portfolio.user_id == current_user.id, Position.is_active),
        ).first()
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found or not owned by user.",
            )
        statement = (
            select(Operation)
            .join(Position, Operation.position_id == Position.id)
            .join(Portfolio, Position.portfolio_id == Portfolio.id)
            .where(
                Operation.position_id == position_id,
                Portfolio.user_id == current_user.id,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(db.exec(statement).scalars().all())

    # If no filter is applied, return all operations across all positions of portfolios owned by the user
    statement = (
        select(Operation)
        .join(Position, Operation.position_id == Position.id)
        .join(Portfolio, Position.portfolio_id == Portfolio.id)
        .where(Portfolio.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())


@router.get(
    "/{operation_id}",
    response_model=OperationRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Operation not found."},
    },
)
def read_operation(
    operation_id: Annotated[int, Path(description="The ID of the operation to retrieve")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Operation:
    """Retrieve details of a specific operation."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    statement = (
        select(Operation)
        .join(Position, Operation.position_id == Position.id)
        .join(Portfolio, Position.portfolio_id == Portfolio.id)
        .where(Operation.id == operation_id, Portfolio.user_id == current_user.id)
    )
    operation = db.exec(statement).scalars().first()
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found.",
        )
    return operation


@router.put(
    "/{operation_id}",
    response_model=OperationRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Operation not found."},
    },
)
def update_operation(
    operation_id: Annotated[int, Path(description="The ID of the operation to update")],
    operation_in: OperationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Operation:
    """Update details of a specific operation, checking ownership."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    statement = (
        select(Operation)
        .join(Position, Operation.position_id == Position.id)
        .join(Portfolio, Position.portfolio_id == Portfolio.id)
        .where(Operation.id == operation_id, Portfolio.user_id == current_user.id)
    )
    operation = db.exec(statement).scalars().first()
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found.",
        )

    update_data = operation_in.model_dump(exclude_unset=True)
    update_data.pop("fees", None)

    for key, value in update_data.items():
        setattr(operation, key, value)

    # We do not overwrite fees cleanly via dict here without explicitly reloading or clearing
    # Assuming update doesn't touch fees unless specifically implemented, but standard pattern:
    operation.updated_at = datetime.now(UTC)
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


@router.delete(
    "/{operation_id}",
    response_model=OperationRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Operation not found."},
    },
)
def delete_operation(
    operation_id: Annotated[int, Path(description="The ID of the operation to delete")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Operation:
    """Delete a specific operation."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    statement = (
        select(Operation)
        .join(Position, Operation.position_id == Position.id)
        .join(Portfolio, Position.portfolio_id == Portfolio.id)
        .where(Operation.id == operation_id, Portfolio.user_id == current_user.id)
    )
    operation = db.exec(statement).scalars().first()
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found.",
        )
    # Operations do not support soft deletes currently (no is_active), so we hard delete.
    db.delete(operation)
    db.commit()
    return operation
