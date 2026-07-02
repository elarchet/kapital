from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session, select

from src.auth import get_current_user
from src.database import get_session
from src.models.financial_account import FinancialAccount
from src.models.institution import Institution
from src.schemas.financial_account import (
    FinancialAccountCreate,
    FinancialAccountRead,
    FinancialAccountUpdate,
)

# Apply authentication gate to all routes in this router at the router level
router = APIRouter(
    prefix="/financial-accounts",
    tags=["financial-accounts"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/",
    response_model=FinancialAccountRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Linked financial institution does not exist."},
    },
)
def create_financial_account(
    account_in: FinancialAccountCreate,
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Create a new financial account (brokerage/savings) held at an Institution."""
    institution = db.exec(
        select(Institution).where(Institution.id == account_in.institution_id, Institution.is_active),
    ).first()
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked financial institution does not exist.",
        )
    db_obj = FinancialAccount(**account_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get("/", response_model=list[FinancialAccountRead])
def read_financial_accounts(
    db: Annotated[Session, Depends(get_session)],
    skip: Annotated[int, Query(ge=0, description="Number of financial accounts to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of financial accounts to return")] = 100,
) -> list[FinancialAccount]:
    """Retrieve list of active financial accounts."""
    statement = select(FinancialAccount).where(FinancialAccount.is_active == True).offset(skip).limit(limit)  # noqa: E712
    return list(db.exec(statement).all())


@router.get(
    "/{account_id}",
    response_model=FinancialAccountRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Financial account not found."},
    },
)
def read_financial_account(
    account_id: Annotated[int, Path(description="The ID of the financial account to retrieve")],
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Retrieve details of a specific financial account."""
    account = db.exec(
        select(FinancialAccount).where(FinancialAccount.id == account_id, FinancialAccount.is_active),
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found.",
        )
    return account


@router.put(
    "/{account_id}",
    response_model=FinancialAccountRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Financial account or new institution not found."},
    },
)
def update_financial_account(
    account_id: Annotated[int, Path(description="The ID of the financial account to update")],
    account_in: FinancialAccountUpdate,
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Update details of a specific financial account."""
    account = db.exec(
        select(FinancialAccount).where(FinancialAccount.id == account_id, FinancialAccount.is_active),
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found.",
        )
    if account_in.institution_id is not None:
        institution = db.exec(
            select(Institution).where(Institution.id == account_in.institution_id, Institution.is_active),
        ).first()
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New financial institution does not exist.",
            )
    update_data = account_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    account.updated_at = datetime.now(UTC)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete(
    "/{account_id}",
    response_model=FinancialAccountRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Financial account not found."},
    },
)
def delete_financial_account(
    account_id: Annotated[int, Path(description="The ID of the financial account to delete")],
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Soft delete a specific financial account."""
    account = db.exec(
        select(FinancialAccount).where(FinancialAccount.id == account_id, FinancialAccount.is_active),
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found.",
        )
    account.is_active = False
    account.deleted_at = datetime.now(UTC)
    db.add(account)
    db.commit()
    return account
