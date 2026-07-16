from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlmodel import Session, select

from src.auth import get_current_user
from src.database import get_session
from src.models.portfolio import Portfolio
from src.models.user import User
from src.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate
from src.services.import_metadata import IMPORT_METADATA
from src.services.import_service import ImportSummary

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post(
    "/",
    response_model=PortfolioRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
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
    db_obj = Portfolio(**portfolio_in.model_dump(), user_id=current_user.id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get(
    "/",
    response_model=list[PortfolioRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def read_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    skip: Annotated[int, Query(ge=0, description="Number of portfolios to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of portfolios to return")] = 100,
) -> list[Portfolio]:
    """Retrieve all active portfolios belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    statement = (
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id, Portfolio.is_active)
        .order_by(Portfolio.sort_order, Portfolio.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.exec(statement).all())


@router.get("/import-metadata", response_model=dict)
def get_import_metadata(
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
) -> dict:
    """Return metadata about importable fields, including required flags and enum values."""
    return IMPORT_METADATA


@router.post(
    "/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def reorder_portfolios(
    portfolio_ids: list[int],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> None:
    """Reorder portfolios in bulk by updating their sort_order."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    # Fetch all active portfolios belonging to the authenticated user
    portfolios = db.exec(
        select(Portfolio).where(
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        ),
    ).all()

    portfolio_map = {p.id: p for p in portfolios if p.id is not None}

    # Batch update sort_order in a single transaction/session commit
    try:
        for idx, p_id in enumerate(portfolio_ids):
            if p_id in portfolio_map:
                portfolio_map[p_id].sort_order = idx
                db.add(portfolio_map[p_id])
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update portfolio order: {e!s}",
        ) from e


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Portfolio not found."},
    },
)
def read_portfolio(
    portfolio_id: Annotated[int, Path(description="The ID of the portfolio to retrieve")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Portfolio:
    """Retrieve a specific portfolio belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    portfolio = db.exec(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        ),
    ).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    return portfolio


@router.put(
    "/{portfolio_id}",
    response_model=PortfolioRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Portfolio not found."},
    },
)
def update_portfolio(
    portfolio_id: Annotated[int, Path(description="The ID of the portfolio to update")],
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
    portfolio = db.exec(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        ),
    ).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    update_data = portfolio_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(portfolio, key, value)
    portfolio.updated_at = datetime.now(UTC)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.delete(
    "/{portfolio_id}",
    response_model=PortfolioRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Portfolio not found."},
    },
)
def delete_portfolio(
    portfolio_id: Annotated[int, Path(description="The ID of the portfolio to delete")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> Portfolio:
    """Soft delete a specific portfolio belonging to the authenticated user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    portfolio = db.exec(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        ),
    ).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    portfolio.is_active = False
    portfolio.deleted_at = datetime.now(UTC)
    db.add(portfolio)
    db.commit()
    return portfolio


@router.post(
    "/{portfolio_id}/import",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "User lacks valid identifier or custom schema JSON is invalid.",
        },
        status.HTTP_404_NOT_FOUND: {"description": "Portfolio not found or not owned by user."},
    },
)
async def import_portfolio_positions(
    portfolio_id: Annotated[int, Path(description="ID of the portfolio to import positions to")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    file: Annotated[
        list[UploadFile],
        File(description="CSV file(s) containing operations data; several files are merged into one batch"),
    ],
    schema_id: Annotated[int | None, Form(description="Schema ID to use for mappings")] = None,
    custom_schema_config: Annotated[
        str | None,
        Form(description="JSON string of custom schema mappings"),
    ] = None,
) -> ImportSummary:
    """Import positions and operations into a portfolio using a file and schema template."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    # Validate portfolio ownership
    portfolio = db.exec(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active,
        ),
    ).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or not owned by user.",
        )

    # Read every uploaded file; they import as one deduplicated batch.
    contents = [await f.read() for f in file]

    # Parse custom schema config JSON string if present
    custom_config = None
    if custom_schema_config:
        try:
            custom_config = json.loads(custom_schema_config)
        except json.JSONDecodeError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid custom_schema_config JSON string.",
            ) from err

    try:
        summary = await import_portfolio_transactions(
            db,
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            file_content=contents,
            schema_id=schema_id,
            custom_schema_config=custom_config,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return summary


# Import import_portfolio_transactions here to avoid circular dependencies
from src.services.import_service import import_portfolio_transactions  # noqa: E402

User.model_rebuild()
