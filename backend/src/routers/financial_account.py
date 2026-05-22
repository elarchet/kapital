from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from src.auth import get_current_user
from src.crud import financial_account_crud, institution_crud
from src.database import get_session
from src.models.financial_account import FinancialAccount
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


@router.post("/", response_model=FinancialAccountRead, status_code=status.HTTP_201_CREATED)
def create_financial_account(
    account_in: FinancialAccountCreate,
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Create a new financial account (brokerage/savings) held at an Institution."""
    institution = institution_crud.get(db, id=account_in.institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked financial institution does not exist.",
        )
    return financial_account_crud.create(db, obj_in=account_in)


@router.get("/", response_model=list[FinancialAccountRead])
def read_financial_accounts(
    db: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 100,
) -> list[FinancialAccount]:
    """Retrieve list of active financial accounts."""
    return financial_account_crud.get_multi(db, skip=skip, limit=limit)


@router.get("/{account_id}", response_model=FinancialAccountRead)
def read_financial_account(
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Retrieve details of a specific financial account."""
    account = financial_account_crud.get(db, id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found.",
        )
    return account


@router.put("/{account_id}", response_model=FinancialAccountRead)
def update_financial_account(
    account_id: int,
    account_in: FinancialAccountUpdate,
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Update details of a specific financial account."""
    account = financial_account_crud.get(db, id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found.",
        )
    if account_in.institution_id is not None:
        institution = institution_crud.get(db, id=account_in.institution_id)
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New financial institution does not exist.",
            )
    return financial_account_crud.update(db, db_obj=account, obj_in=account_in)


@router.delete("/{account_id}", response_model=FinancialAccountRead)
def delete_financial_account(
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
) -> FinancialAccount:
    """Soft delete a specific financial account."""
    account = financial_account_crud.get(db, id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial account not found.",
        )
    financial_account_crud.remove(db, id=account_id)
    return account
