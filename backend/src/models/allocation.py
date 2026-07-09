"""Allocation model — a user-defined split of a RawTransaction to a Position.

A single :class:`~src.models.raw_transaction.RawTransaction` can be segmented
into many ``Allocation`` records (1-to-Many), each routing part of the parent
transaction to a :class:`~src.models.position.Position` inside a portfolio.

The split can be expressed three ways via :class:`AllocationMethod`:

- ``QUANTITY``   — allocate a fixed number of shares/units.
- ``PERCENTAGE`` — allocate a percentage of the parent's quantity/amount.
- ``AMOUNT``     — allocate a flat fiat amount.

``value`` stores the user's raw input in the chosen unit; ``quantity`` and
``amount`` store the resolved figures so downstream services never re-derive
the split. Allocations always trace back to their parent transaction, so splits
can be recombined or reconciled at any time.
"""

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from src.models.position import Position
    from src.models.raw_transaction import RawTransaction


class AllocationMethod(StrEnum):
    """How a split value is interpreted when allocating a raw transaction."""

    QUANTITY = "quantity"
    PERCENTAGE = "percentage"
    AMOUNT = "amount"


class Allocation(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """A portion of a RawTransaction routed to a single Position."""

    __tablename__ = "allocation"

    id: int | None = Field(default=None, primary_key=True)

    method: AllocationMethod = Field(
        default=AllocationMethod.PERCENTAGE,
        nullable=False,
    )
    value: Decimal = Field(nullable=False, max_digits=20, decimal_places=8)

    # Resolved figures (derived from ``method`` + ``value`` at split time).
    quantity: Decimal = Field(default=Decimal(0), nullable=False, max_digits=20, decimal_places=8)
    amount: Decimal = Field(default=Decimal(0), nullable=False, max_digits=20, decimal_places=8)
    currency: str = Field(default="EUR", nullable=False, max_length=3)

    # The default 100% allocation auto-created on ingestion.
    is_default: bool = Field(default=False, nullable=False)
    notes: str | None = Field(default=None, max_length=300)

    # -- foreign keys ----------------------------------------------------------
    raw_transaction_id: int = Field(
        foreign_key="raw_transaction.id",
        nullable=False,
        index=True,
    )
    position_id: int = Field(
        foreign_key="position.id",
        nullable=False,
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    raw_transaction: "RawTransaction" = Relationship(back_populates="allocations")
    position: "Position" = Relationship(back_populates="allocations")
