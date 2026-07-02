from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session, select

from src.auth import get_current_user
from src.crud import portfolio_crud, position_crud
from src.database import get_session
from src.models.portfolio import Portfolio
from src.models.position import Position
from src.models.user import User
from src.schemas.cost_basis import CostBasisRead
from src.schemas.position import PositionCreate, PositionRead, PositionUpdate
from src.services.cost_basis_service import CostBasisResult, get_position_cost_basis

router = APIRouter(prefix="/positions", tags=["positions"])


@router.post(
    "/",
    response_model=PositionRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Parent portfolio not found or not owned by user."},
    },
)
def create_position(
    position_in: PositionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Position:
    """Create a new position within a portfolio owned by the current user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    # Validate portfolio ownership
    portfolio = portfolio_crud.get_by_owner(db, id=position_in.portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent portfolio not found or not owned by user.",
        )
    return position_crud.create(db, obj_in=position_in)


@router.get(
    "/",
    response_model=list[PositionRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Filtered portfolio not found or not owned by user."},
    },
)
def read_positions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    portfolio_id: Annotated[int | None, Query(description="Filter positions by a specific portfolio ID")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of positions to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of positions to return")] = 100,
) -> list[Position]:
    """Retrieve all active positions belonging to the user.

    Can optionally filter by portfolio_id.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    if portfolio_id is not None:
        portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found or not owned by user.",
            )
        return position_crud.get_multi_by_portfolio(
            db,
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )

    # If no portfolio filter is applied, return all positions across all portfolios owned by the user
    statement = (
        select(Position)
        .join(Portfolio)
        .where(Portfolio.user_id == current_user.id, Position.is_active == True)  # noqa: E712
        .offset(skip)
        .limit(limit)
    )
    return list(db.exec(statement).all())


@router.get(
    "/{position_id}/cost_basis",
    response_model=CostBasisRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Position not found."},
    },
)
def read_position_cost_basis(
    position_id: Annotated[int, Path(description="The ID of the position to retrieve cost basis for")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> CostBasisResult:
    """Retrieve the split-adjusted cost basis details for a specific position."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    position = position_crud.get_by_owner(db, id=position_id, user_id=current_user.id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found or not owned by user.",
        )
    return get_position_cost_basis(db, position_id=position_id)


@router.get(
    "/{position_id}",
    response_model=PositionRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Position not found."},
    },
)
def read_position(
    position_id: Annotated[int, Path(description="The ID of the position to retrieve")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Position:
    """Retrieve details of a specific position."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    position = position_crud.get_by_owner(db, id=position_id, user_id=current_user.id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found.",
        )
    return position


@router.put(
    "/{position_id}",
    response_model=PositionRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Position or new portfolio not found."},
    },
)
def update_position(
    position_id: Annotated[int, Path(description="The ID of the position to update")],
    position_in: PositionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Position:
    """Update details of a specific position, validating ownership."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    position = position_crud.get_by_owner(db, id=position_id, user_id=current_user.id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found.",
        )
    # If portfolio_id is changing, validate the new portfolio belongs to the user
    if position_in.portfolio_id is not None:
        portfolio = portfolio_crud.get_by_owner(db, id=position_in.portfolio_id, user_id=current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New portfolio not found or not owned by user.",
            )
    return position_crud.update(db, db_obj=position, obj_in=position_in)


@router.delete(
    "/{position_id}",
    response_model=PositionRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Position not found."},
    },
)
def delete_position(
    position_id: Annotated[int, Path(description="The ID of the position to delete")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Position:
    """Soft delete a specific position."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    position = position_crud.get_by_owner(db, id=position_id, user_id=current_user.id)
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found.",
        )
    position_crud.remove(db, id=position_id)
    return position
