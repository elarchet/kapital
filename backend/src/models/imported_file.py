"""ImportedFile model — a user's uploaded import file, persisted in object storage.

Every file that goes through the import wizard is stored once per user:
``(user_id, sha256)`` uniqueness makes re-uploads reuse the existing object
and row instead of storing a duplicate. The stored bytes are the audit source
of truth and allow re-importing (or re-mapping fields) later without asking
the user for the file again. ``storage_key`` locates the object in the
configured storage backend (see ``services.storage``).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class ImportedFile(TimestampMixin, SQLModel, table=True):
    """A deduplicated, durably stored import file owned by one user."""

    __tablename__ = "imported_file"
    __table_args__ = (UniqueConstraint("user_id", "sha256", name="uq_imported_file_user_sha"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    sha256: str = Field(nullable=False, max_length=64, index=True)
    filename: str = Field(nullable=False, max_length=255)
    size_bytes: int = Field(nullable=False)
    content_type: str | None = Field(default=None, max_length=100)
    storage_key: str = Field(nullable=False, max_length=255)
    # NULL while the file has only been loaded into the wizard; set (and bumped
    # on every reuse) once its transactions are actually imported. created_at
    # keeps the first time the file was seen.
    last_imported_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )

    user: "User" = Relationship()
