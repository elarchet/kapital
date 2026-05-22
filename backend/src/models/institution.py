"""Institution model — a bank, broker, or exchange."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.financial_account import FinancialAccount


class Institution(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """A financial institution (bank, broker, exchange, etc.)."""

    __tablename__ = "institution"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False, max_length=300)
    country: str | None = Field(default=None, max_length=2)
    website: str | None = Field(default=None, max_length=500)

    # -- relationships ---------------------------------------------------------
    financial_accounts: list["FinancialAccount"] = Relationship(
        back_populates="institution",
    )
