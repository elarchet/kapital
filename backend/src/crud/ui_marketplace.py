from __future__ import annotations

from sqlmodel import Session, select

from src.crud.base import CRUDBase
from src.models.ui_marketplace import UIComponentOverride, UIComponentVariant
from src.schemas.ui_marketplace import (
    UIComponentOverrideCreate,
    UIComponentVariantCreate,
    UIComponentVariantUpdate,
)


class CRUDUIComponentVariant(
    CRUDBase[UIComponentVariant, UIComponentVariantCreate, UIComponentVariantUpdate],
):
    """UIComponentVariant CRUD operations."""

    def get_multi_by_user_or_public(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UIComponentVariant]:
        """Fetch all active public variants or variants owned by the user."""
        statement = (
            select(UIComponentVariant)
            .where(
                (UIComponentVariant.user_id == user_id) | UIComponentVariant.is_public,
                UIComponentVariant.is_active,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(db.exec(statement).all())

    def get_by_owner_or_public(
        self,
        db: Session,
        *,
        id: int,
        user_id: int,
    ) -> UIComponentVariant | None:
        """Fetch an active variant by ID if it belongs to the user or is public."""
        statement = select(UIComponentVariant).where(
            UIComponentVariant.id == id,
            (UIComponentVariant.user_id == user_id) | UIComponentVariant.is_public,
            UIComponentVariant.is_active,
        )
        return db.exec(statement).first()


class CRUDUIComponentOverride(
    CRUDBase[UIComponentOverride, UIComponentOverrideCreate, None],
):
    """UIComponentOverride CRUD operations."""

    def get_by_user_and_key(
        self,
        db: Session,
        *,
        user_id: int,
        component_key: str,
    ) -> UIComponentOverride | None:
        """Fetch override for a user and key."""
        statement = select(UIComponentOverride).where(
            UIComponentOverride.user_id == user_id,
            UIComponentOverride.component_key == component_key,
            UIComponentOverride.is_active,
        )
        return db.exec(statement).first()

    def get_all_by_user(
        self,
        db: Session,
        *,
        user_id: int,
    ) -> list[UIComponentOverride]:
        """Fetch all active overrides for a user."""
        statement = select(UIComponentOverride).where(
            UIComponentOverride.user_id == user_id,
            UIComponentOverride.is_active,
        )
        return list(db.exec(statement).all())


ui_component_variant_crud = CRUDUIComponentVariant(UIComponentVariant)
ui_component_override_crud = CRUDUIComponentOverride(UIComponentOverride)
