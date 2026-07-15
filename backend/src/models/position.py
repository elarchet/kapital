"""Position model and AssetType enum."""

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.allocation import Allocation
    from src.models.portfolio import Portfolio


class AssetType(StrEnum):
    """Supported financial asset categories."""

    CASH = "cash"
    CRYPTO = "crypto"
    ETF = "etf"
    STOCK = "stock"
    BOND = "bond"
    COMMODITY = "commodity"
    FUND = "fund"
    OTHER = "other"


class Position(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """A single financial position (holding) within a Portfolio.

    Tracks the current quantity of a specific asset. The full history of
    changes is recorded via linked :class:`Operation` records.
    """

    __tablename__ = "position"

    id: int | None = Field(default=None, primary_key=True)
    asset_type: AssetType = Field(nullable=False, index=True)
    ticker: str | None = Field(default=None, max_length=20, index=True)
    name: str | None = Field(default=None, nullable=True, max_length=300)
    isin: str | None = Field(default=None, max_length=12, index=True)
    quantity: Decimal = Field(
        default=Decimal(0),
        nullable=False,
        max_digits=20,
        decimal_places=8,
    )
    currency: str = Field(default="EUR", nullable=False, max_length=3)

    # -- foreign keys ----------------------------------------------------------
    portfolio_id: int = Field(
        foreign_key="portfolio.id",
        nullable=False,
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    portfolio: "Portfolio" = Relationship(back_populates="positions")
    allocations: list["Allocation"] = Relationship(back_populates="position")
