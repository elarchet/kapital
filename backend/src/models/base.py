"""Shared base classes, mixins, and registry for Kapital models.

Provides:
- A shared SQLAlchemy registry so SQLModel tables and pure-SQLAlchemy STI
  tables (Operation hierarchy) coexist under one metadata.
- TimestampMixin: created_at / updated_at audit columns.
- SoftDeleteMixin: is_active flag + deleted_at timestamp.
- generate_public_id(): deterministic UUID4 factory for public API IDs.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, registry
from sqlmodel import Field, SQLModel

# ---------------------------------------------------------------------------
# Shared registry — binds SQLModel and pure-SQLAlchemy models to the same
# metadata so a single ``create_all()`` call builds every table.
# ---------------------------------------------------------------------------
shared_registry: registry = SQLModel._sa_registry  # type: ignore[attr-defined]  # noqa: SLF001


class SABase(DeclarativeBase):
    """Pure-SQLAlchemy declarative base that shares SQLModel's registry.

    Used exclusively by the Operation STI hierarchy.
    """

    registry = shared_registry


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` audit columns."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
        },
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": lambda: datetime.now(UTC),
        },
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds ``is_active`` flag and ``deleted_at`` timestamp for soft deletes."""

    is_active: bool = Field(default=True, nullable=False, index=True)
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_public_id() -> UUID:
    """Generate a UUID4 for use as a public-facing identifier."""
    return uuid4()
