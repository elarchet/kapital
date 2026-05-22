from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from src.crud.base import CRUDBase
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """User CRUD operations, handling argon2id password hashing."""

    def get_by_email(self, db: Session, email: str) -> User | None:
        """Retrieve an active user by their email address."""
        statement = select(User).where(User.email == email, User.is_active == True)  # noqa: E712
        return db.exec(statement).first()

    def get_by_public_id(self, db: Session, public_id: UUID) -> User | None:
        """Retrieve an active user by their externally exposed public UUID4."""
        statement = select(User).where(User.public_id == public_id, User.is_active == True)  # noqa: E712
        return db.exec(statement).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user, automatically hashing their plain password."""
        db_obj = User(
            email=obj_in.email,
            hashed_password="",  # Will be set by set_password
        )
        db_obj.set_password(obj_in.password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: User,
        obj_in: UserUpdate | dict[str, Any],
    ) -> User:
        """Update user profile, hashing password if updated."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        if update_data.get("password"):
            db_obj.set_password(update_data["password"])
            del update_data["password"]

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(self, db: Session, email: str, password: str) -> User | None:
        """Verify user credentials and return user object if successful."""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not user.verify_password(password):
            return None
        return user


user_crud = CRUDUser(User)
