from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session, select

from src.auth import get_current_user
from src.crud import financial_account_crud, operation_crud, position_crud
from src.database import get_session
from src.models.operation import Operation
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
    position = position_crud.get_by_owner(db, id=operation_in.position_id, user_id=current_user.id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked position not found or not owned by user.",
        )

    # 2. Validate financial account existence
    account = financial_account_crud.get(db, id=operation_in.financial_account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked financial account not found.",
        )

    return operation_crud.create(db, obj_in=operation_in)


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
        position = position_crud.get_by_owner(db, id=position_id, user_id=current_user.id)
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found or not owned by user.",
            )
        return operation_crud.get_multi_by_position(
            db,
            position_id=position_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )

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
    operation = operation_crud.get_by_owner(db, id=operation_id, user_id=current_user.id)
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
    operation = operation_crud.get_by_owner(db, id=operation_id, user_id=current_user.id)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found.",
        )
    return operation_crud.update(db, db_obj=operation, obj_in=operation_in)


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
    operation = operation_crud.get_by_owner(db, id=operation_id, user_id=current_user.id)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found.",
        )
    operation_crud.remove(db, id=operation_id)
    return operation
