from __future__ import annotations

from sqlmodel import Session, select

from src.crud.base import CRUDBase
from src.models.import_file_schema import ImportFileSchema
from src.schemas.import_file_schema import ImportFileSchemaCreate, ImportFileSchemaUpdate


class CRUDImportFileSchema(CRUDBase[ImportFileSchema, ImportFileSchemaCreate, ImportFileSchemaUpdate]):
    """ImportFileSchema CRUD operations."""

    def get_multi_by_user_or_public(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ImportFileSchema]:
        """Fetch all active public schemas or schemas owned by the user."""
        statement = (
            select(ImportFileSchema)
            .where(
                (ImportFileSchema.user_id == user_id) | ImportFileSchema.is_public,
                ImportFileSchema.is_active,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(db.exec(statement).all())

    def get_by_owner_or_public(self, db: Session, *, id: int, user_id: int) -> ImportFileSchema | None:
        """Fetch an active schema by ID if it belongs to the user or is public."""
        statement = select(ImportFileSchema).where(
            ImportFileSchema.id == id,
            (ImportFileSchema.user_id == user_id) | ImportFileSchema.is_public,
            ImportFileSchema.is_active,
        )
        return db.exec(statement).first()


import_file_schema_crud = CRUDImportFileSchema(ImportFileSchema)
