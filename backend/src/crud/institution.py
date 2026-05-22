from __future__ import annotations

from src.crud.base import CRUDBase
from src.models.institution import Institution
from src.schemas.institution import InstitutionCreate, InstitutionUpdate


class CRUDInstitution(CRUDBase[Institution, InstitutionCreate, InstitutionUpdate]):
    """Institution CRUD operations."""


institution_crud = CRUDInstitution(Institution)
