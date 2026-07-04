"""Portfolio model — groups Positions under a User."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.position import Position
    from src.models.user import User


class Portfolio(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """A named collection of financial positions owned by a User."""

    __tablename__ = "portfolio"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    emoji: str | None = Field(default=None, max_length=20)
    sort_order: int = Field(default=0, nullable=False)

    # -- foreign keys ----------------------------------------------------------
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)

    # -- relationships ---------------------------------------------------------
    user: "User" = Relationship(back_populates="portfolios")
    positions: list["Position"] = Relationship(back_populates="portfolio")
