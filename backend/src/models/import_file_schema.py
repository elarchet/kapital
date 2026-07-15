"""ImportFileSchema model."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class ImportFileSchema(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """Configuration mapping standardizing file formats (e.g. CSV) to our models."""

    __tablename__ = "import_file_schema"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=150)
    is_public: bool = Field(default=False, nullable=False)

    # CSV format preferences
    delimiter: str = Field(default=",", max_length=5)
    decimal_separator: str = Field(default=".", max_length=5)

    # JSON mappings stored as serialized text
    mappings: str = Field(default="{}", nullable=False)

    is_incomplete: bool = Field(default=False, nullable=False)

    # -- institution abstraction ----------------------------------------------
    # A template targets a single institution; every row in an uploaded file is
    # assumed to originate from this institution. ``institution_key`` is a
    # stable slug (e.g. "trading212") that selects the built-in parser profile,
    # while ``institution_id`` optionally binds the template to a stored
    # Institution record.
    institution_key: str = Field(default="custom", nullable=False, max_length=50, index=True)
    institution_id: int | None = Field(
        default=None,
        foreign_key="institution.id",
        nullable=True,
        index=True,
    )

    # -- foreign keys ----------------------------------------------------------
    user_id: int | None = Field(
        default=None,
        foreign_key="user.id",
        nullable=True,
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    user: "User" = Relationship(back_populates="import_file_schemas")
