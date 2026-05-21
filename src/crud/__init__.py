from __future__ import annotations

from src.crud.financial_account import financial_account_crud
from src.crud.institution import institution_crud
from src.crud.operation import operation_crud
from src.crud.portfolio import portfolio_crud
from src.crud.position import position_crud
from src.crud.user import user_crud

__all__ = [
    "financial_account_crud",
    "institution_crud",
    "operation_crud",
    "portfolio_crud",
    "position_crud",
    "user_crud",
]
