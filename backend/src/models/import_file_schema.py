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

    # -- foreign keys ----------------------------------------------------------
    user_id: int | None = Field(
        default=None,
        foreign_key="user.id",
        nullable=True,
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    user: "User" = Relationship(back_populates="import_file_schemas")
