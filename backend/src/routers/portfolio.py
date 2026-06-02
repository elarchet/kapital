from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlmodel import Session

from src.auth import get_current_user
from src.crud import portfolio_crud
from src.database import get_session
from src.models.portfolio import Portfolio
from src.models.user import User
from src.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate
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
    return portfolio_crud.create_with_owner(db, obj_in=portfolio_in, user_id=current_user.id)


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
    return portfolio_crud.get_multi_by_owner(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/import-metadata", response_model=dict)
def get_import_metadata(
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
) -> dict:
    """Return metadata about importable fields, including required flags and enum values."""
    return {
        "fields": [
            {
                "key": "operation_type",
                "label": "Action / Type",
                "is_required": True,
                "type": "enum",
                "enum_values": [
                    "buy",
                    "sell",
                    "dividend",
                    "interest",
                    "expense",
                    "revenue",
                    "fx_rate_change",
                    "transfer_in",
                    "transfer_out",
                    "stock_split",
                    "fee",
                    "tax",
                    "limit_buy",
                    "limit_sell",
                ],
            },
            {
                "key": "executed_at",
                "label": "Timestamp",
                "is_required": True,
                "type": "datetime",
            },
            {
                "key": "name",
                "label": "Asset Name / Label",
                "is_required": True,
                "type": "string",
            },
            {
                "key": "total_amount",
                "label": "Total Amount",
                "is_required": True,
                "type": "numeric",
            },
            {
                "key": "currency",
                "label": "Total Currency",
                "is_required": True,
                "type": "string",
            },
            {
                "key": "ticker",
                "label": "Ticker Symbol",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "isin",
                "label": "ISIN Number",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "quantity",
                "label": "Quantity",
                "is_required": False,
                "type": "numeric",
            },
            {
                "key": "unit_price",
                "label": "Price Per Share",
                "is_required": False,
                "type": "numeric",
            },
            {
                "key": "price_currency",
                "label": "Price Currency",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "transaction_id",
                "label": "Transaction ID",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "exchange_rate",
                "label": "Exchange Rate",
                "is_required": False,
                "type": "numeric",
            },
            {
                "key": "fee_amount",
                "label": "Fee Amount",
                "is_required": False,
                "type": "numeric",
            },
            {
                "key": "fee_currency",
                "label": "Fee Currency",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "fee_type",
                "label": "Fee Type",
                "is_required": False,
                "type": "enum",
                "enum_values": ["conversion", "withholding_tax", "commission", "transaction", "other"],
            },
            {
                "key": "tax_amount",
                "label": "Tax Amount",
                "is_required": False,
                "type": "numeric",
            },
            {
                "key": "tax_currency",
                "label": "Tax Currency",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "merchant_name",
                "label": "Merchant Name",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "merchant_category",
                "label": "Merchant Category",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "source_reference",
                "label": "Source Reference",
                "is_required": False,
                "type": "string",
            },
            {
                "key": "destination_reference",
                "label": "Destination Reference",
                "is_required": False,
                "type": "string",
            },
        ],
    }


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
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
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
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    return portfolio_crud.update(db, db_obj=portfolio, obj_in=portfolio_in)


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
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )
    # Generic base remove method handles soft deletes if model inherits from SoftDeleteMixin
    portfolio_crud.remove(db, id=portfolio_id)
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
    file: Annotated[UploadFile, File(description="CSV/Excel file containing position operations data")],
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
    portfolio = portfolio_crud.get_by_owner(db, id=portfolio_id, user_id=current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or not owned by user.",
        )

    # Read file content
    contents = await file.read()

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
        summary = import_portfolio_transactions(
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
