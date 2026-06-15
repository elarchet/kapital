"""User model with argon2id password hashing."""

from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin, generate_public_id

# argon2id hasher with OWASP-recommended defaults
_ph = PasswordHasher()


class User(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """Application user.

    Uses ``public_id`` (UUID4) as the externally-visible identifier in the
    FastAPI layer — the integer ``id`` is never exposed over the API.
    """

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(
        default_factory=generate_public_id,
        unique=True,
        index=True,
        nullable=False,
    )
    email: str = Field(unique=True, index=True, nullable=False, max_length=320)
    hashed_password: str = Field(nullable=False, max_length=512)
    theme: str = Field(default="slate-light", nullable=False, max_length=50)

    # -- relationships ---------------------------------------------------------
    portfolios: list["Portfolio"] = Relationship(back_populates="user")
    import_file_schemas: list["ImportFileSchema"] = Relationship(back_populates="user")
    ui_component_variants: list["UIComponentVariant"] = Relationship(back_populates="user")
    ui_component_overrides: list["UIComponentOverride"] = Relationship(back_populates="user")

    # -- password helpers ------------------------------------------------------

    def set_password(self, plain_password: str) -> None:
        """Hash *plain_password* with argon2id and store the result."""
        self.hashed_password = _ph.hash(plain_password)

    def verify_password(self, plain_password: str) -> bool:
        """Return ``True`` if *plain_password* matches the stored hash.

        Automatically re-hashes if the existing hash uses outdated parameters.
        """
        try:
            valid = _ph.verify(self.hashed_password, plain_password)
        except VerifyMismatchError:
            return False

        # Transparently upgrade hash parameters when they change.
        if valid and _ph.check_needs_rehash(self.hashed_password):
            self.hashed_password = _ph.hash(plain_password)

        return valid


# Prevent circular import — used only for type annotations above.
from src.models.import_file_schema import ImportFileSchema  # noqa: E402
from src.models.portfolio import Portfolio  # noqa: E402
from src.models.ui_marketplace import UIComponentOverride, UIComponentVariant  # noqa: E402

User.model_rebuild()
