"""Database models for the UI Component Marketplace."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class UIComponentVariant(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """An available variant/template in the UI Component Marketplace.

    Acts similarly to ImportFileSchema, separating system-wide public custom variants
    from user-created custom component options.
    """

    __tablename__ = "ui_component_variant"

    id: int | None = Field(default=None, primary_key=True)

    # Logical identifier of the target component (e.g., 'sidebar', 'custom-dropdown')
    component_key: str = Field(nullable=False, index=True, max_length=100)

    name: str = Field(nullable=False, max_length=150)
    description: str = Field(default="", max_length=500)

    # URL pointing to the sandboxed compiled script or Vue ESM bundle asset
    asset_url: str = Field(nullable=False, max_length=500)

    # Visibility logic matching the import file schema pattern
    is_public: bool = Field(default=False, nullable=False)

    user_id: int | None = Field(
        default=None,
        foreign_key="user.id",
        nullable=True,
        index=True,
    )

    # Relationships
    user: "User" = Relationship(back_populates="ui_component_variants")
    overrides: list["UIComponentOverride"] = Relationship(back_populates="variant")


class UIComponentOverride(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """Maps a user's choice of override variant for a given component key.

    If no entry exists for a user and component_key, the system falls back
    instantly to the built-in system component.
    """

    __tablename__ = "ui_component_override"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    component_key: str = Field(nullable=False, index=True, max_length=100)

    variant_id: int = Field(
        foreign_key="ui_component_variant.id",
        nullable=False,
        index=True,
    )

    # Relationships
    user: "User" = Relationship(back_populates="ui_component_overrides")
    variant: "UIComponentVariant" = Relationship(back_populates="overrides")
