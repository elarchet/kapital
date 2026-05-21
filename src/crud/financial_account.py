from __future__ import annotations

from src.crud.base import CRUDBase
from src.models.financial_account import FinancialAccount
from src.schemas.financial_account import FinancialAccountCreate, FinancialAccountUpdate


class CRUDFinancialAccount(
    CRUDBase[FinancialAccount, FinancialAccountCreate, FinancialAccountUpdate],
):
    """Financial account CRUD operations."""


financial_account_crud = CRUDFinancialAccount(FinancialAccount)
