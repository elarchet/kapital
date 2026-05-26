from __future__ import annotations

from src.crud.base import CRUDBase
from src.models.fee import Fee
from src.schemas.fee import FeeCreate


class CRUDFee(CRUDBase[Fee, FeeCreate, FeeCreate]):
    """Fee CRUD operations."""


fee_crud = CRUDFee(Fee)
