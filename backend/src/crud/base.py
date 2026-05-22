from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select


class CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]:
    """Generic CRUD operations base class using PEP 695 type parameters.

    Automatically handles soft deletes if the model class includes `is_active`.
    """

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    def get(self, db: Session, id: Any) -> ModelType | None:
        """Fetch a single record by primary key."""
        obj = db.get(self.model, id)
        # If model supports soft delete, verify it is active
        if obj and hasattr(obj, "is_active") and not obj.is_active:
            return None
        return obj

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Fetch multiple records, respecting soft delete filtering."""
        statement = select(self.model)
        if hasattr(self.model, "is_active"):
            # Use getattr on the model class to build the query expression
            statement = statement.where(self.model.is_active == True)  # noqa: E712
        statement = statement.offset(skip).limit(limit)
        return list(db.exec(statement).all())

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Insert a new record from a Pydantic create schema."""
        # Convert schema to dict and build the model
        obj_in_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update an existing record, modifying only specified attributes."""
        obj_data = db_obj.model_dump() if hasattr(db_obj, "model_dump") else db_obj.__dict__
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        # Automatically update updated_at if the mixin is present
        if hasattr(db_obj, "updated_at"):
            db_obj.updated_at = datetime.now(UTC)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType | None:
        """Perform a soft delete if supported, otherwise a hard delete."""
        obj = db.get(self.model, id)
        if not obj:
            return None

        if hasattr(obj, "is_active"):
            obj.is_active = False
            if hasattr(obj, "deleted_at"):
                obj.deleted_at = datetime.now(UTC)
            db.add(obj)
        else:
            db.delete(obj)

        db.commit()
        return obj
