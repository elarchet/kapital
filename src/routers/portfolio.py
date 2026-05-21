from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from src.auth import get_current_user
from src.crud import portfolio_crud
from src.database import get_session
from src.models.portfolio import Portfolio
from src.models.user import User
from src.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("/", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    portfolio_in: PortfolioCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Portfolio:
    """Create a new portfolio bound to the current authenticated user."""
    # Ensure current_user.id is resolved
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    return portfolio_crud.create_with_owner(db, obj_in=portfolio_in, user_id=current_user.id)


@router.get("/", response_model=list[PortfolioRead])
def read_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 100,
) -> list[Portfolio]:
    """Retrieve all active portfolios belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    return portfolio_crud.get_multi_by_owner(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def read_portfolio(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Portfolio:
    """Retrieve a specific portfolio belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    return portfolio


@router.put("/{portfolio_id}", response_model=PortfolioRead)
def update_portfolio(
    portfolio_id: int,
    portfolio_in: PortfolioUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Portfolio:
    """Update a specific portfolio belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    return portfolio_crud.update(db, db_obj=portfolio, obj_in=portfolio_in)


@router.delete("/{portfolio_id}", response_model=PortfolioRead)
def delete_portfolio(
    portfolio_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Portfolio:
    """Soft delete a specific portfolio belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    # Generic base remove method handles soft deletes if model inherits from SoftDeleteMixin
    portfolio_crud.remove(db, id=portfolio_id)
    return portfolio


User.model_rebuild()
