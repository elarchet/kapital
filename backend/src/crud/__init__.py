from __future__ import annotations

from src.crud.base import CRUDBase
from src.crud.import_file_schema import import_file_schema_crud
from src.crud.operation import operation_crud
from src.crud.portfolio import portfolio_crud
from src.crud.position import position_crud
from src.crud.user import user_crud
from src.models.fee import Fee
from src.models.financial_account import FinancialAccount
from src.models.institution import Institution
from src.schemas.fee import FeeCreate
from src.schemas.financial_account import FinancialAccountCreate, FinancialAccountUpdate
from src.schemas.institution import InstitutionCreate, InstitutionUpdate

fee_crud = CRUDBase[Fee, FeeCreate, FeeCreate](Fee)
financial_account_crud = CRUDBase[FinancialAccount, FinancialAccountCreate, FinancialAccountUpdate](FinancialAccount)
institution_crud = CRUDBase[Institution, InstitutionCreate, InstitutionUpdate](Institution)

__all__ = [
    "fee_crud",
    "financial_account_crud",
    "import_file_schema_crud",
    "institution_crud",
    "operation_crud",
    "portfolio_crud",
    "position_crud",
    "user_crud",
]
