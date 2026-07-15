"""Fee model and FeeType enum."""

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.raw_transaction import RawTransaction


class FeeType(StrEnum):
    """Categorization of fees/taxes."""

    CONVERSION = "conversion"
    WITHHOLDING_TAX = "withholding_tax"
    COMMISSION = "commission"
    TRANSACTION = "transaction"
    OTHER = "other"


class Fee(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """An itemized fee or tax associated with a raw transaction."""

    __tablename__ = "fee"

    id: int | None = Field(default=None, primary_key=True)
    amount: Decimal = Field(
        nullable=False,
        max_digits=20,
        decimal_places=8,
    )
    currency: str = Field(nullable=False, max_length=3)
    fee_type: FeeType = Field(nullable=False, index=True)
    notes: str | None = Field(default=None, max_length=300)

    # -- foreign keys ----------------------------------------------------------
    raw_transaction_id: int = Field(
        foreign_key="raw_transaction.id",
        nullable=False,
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    raw_transaction: "RawTransaction" = Relationship(back_populates="fees")
