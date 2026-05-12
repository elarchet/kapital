"""Operation model — pure SQLAlchemy Single Table Inheritance.

This module deliberately uses SQLAlchemy's DeclarativeBase (via ``SABase``)
instead of SQLModel because SQLModel does not support polymorphic STI.
The ``SABase`` class shares SQLModel's registry, so all tables are created
together with a single ``metadata.create_all()`` call.

Querying ``select(Operation)`` returns the correct subclass instance
(``BuyOperation``, ``DividendOperation``, etc.) based on the discriminator.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import SABase

if TYPE_CHECKING:
    from src.models.financial_account import FinancialAccount
    from src.models.position import Position


class Operation(SABase):
    """Base operation — the single ``operation`` table.

    Every subclass maps to this same table via the ``operation_type``
    discriminator column.  Columns specific to a subclass are nullable
    at the DB level and only populated for the relevant type.
    """

    __tablename__ = "operation"

    # -- primary key & discriminator -------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # -- common columns --------------------------------------------------------
    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
    )
    unit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -- foreign keys ----------------------------------------------------------
    position_id: Mapped[int] = mapped_column(
        ForeignKey("position.id"),
        nullable=False,
    )
    financial_account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_account.id"),
        nullable=False,
    )

    # -- audit -----------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"),
    )

    # -- relationships ---------------------------------------------------------
    position: Mapped[Position] = relationship(
        back_populates="operations",
        foreign_keys=[position_id],
    )
    financial_account: Mapped[FinancialAccount] = relationship(
        back_populates="operations",
        foreign_keys=[financial_account_id],
    )

    # -- STI mapper config -----------------------------------------------------
    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_on": operation_type,
        "polymorphic_identity": "operation",
    }

    # -- indexes ---------------------------------------------------------------
    __table_args__ = (
        Index("ix_operation_position_id", "position_id"),
        Index("ix_operation_financial_account_id", "financial_account_id"),
        Index("ix_operation_executed_at", "executed_at"),
        Index("ix_operation_type", "operation_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}(id={self.id}, "
            f"type={self.operation_type}, "
            f"amount={self.total_amount} {self.currency})>"
        )


# ---------------------------------------------------------------------------
# Market order subclasses
# ---------------------------------------------------------------------------


class BuyOperation(Operation):
    """A market buy order."""

    __mapper_args__: ClassVar[dict[str, object]] = {"polymorphic_identity": "buy"}


class SellOperation(Operation):
    """A market sell order."""

    __mapper_args__: ClassVar[dict[str, object]] = {"polymorphic_identity": "sell"}


class LimitBuyOperation(Operation):
    """A limit buy order — ``limit_price`` is required."""

    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_identity": "limit_buy",
    }

    limit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        default=None,
    )


class LimitSellOperation(Operation):
    """A limit sell order — ``limit_price`` is required."""

    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_identity": "limit_sell",
    }

    limit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        default=None,
        use_existing_column=True,
    )


# ---------------------------------------------------------------------------
# Income / cost subclasses
# ---------------------------------------------------------------------------


class DividendOperation(Operation):
    """A dividend payment — ``dividend_per_share`` is required."""

    __mapper_args__: ClassVar[dict[str, object]] = {"polymorphic_identity": "dividend"}

    dividend_per_share: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8),
        nullable=True,
        default=None,
    )


class FeeOperation(Operation):
    """A fee charge — ``fee_category`` describes the kind of fee."""

    __mapper_args__: ClassVar[dict[str, object]] = {"polymorphic_identity": "fee"}

    fee_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )


class TaxOperation(Operation):
    """A tax charge — ``tax_category`` describes the kind of tax."""

    __mapper_args__: ClassVar[dict[str, object]] = {"polymorphic_identity": "tax"}

    tax_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
    )


class InterestOperation(Operation):
    """Interest received or paid on cash balances."""

    __mapper_args__: ClassVar[dict[str, object]] = {"polymorphic_identity": "interest"}


# ---------------------------------------------------------------------------
# Transfer subclasses
# ---------------------------------------------------------------------------


class TransferInOperation(Operation):
    """An incoming transfer — ``source_reference`` tracks the origin."""

    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_identity": "transfer_in",
    }

    source_reference: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        default=None,
    )


class TransferOutOperation(Operation):
    """An outgoing transfer — ``destination_reference`` tracks the target."""

    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_identity": "transfer_out",
    }

    destination_reference: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        default=None,
    )


# ---------------------------------------------------------------------------
# Corporate action & FX subclasses
# ---------------------------------------------------------------------------


class StockSplitOperation(Operation):
    """A stock split — ``split_ratio`` is required (e.g. 4.0 for a 4-for-1)."""

    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_identity": "stock_split",
    }

    split_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=6),
        nullable=True,
        default=None,
    )


class FxRateChangeOperation(Operation):
    """A currency exchange operation.

    ``source_currency``, ``target_currency``, and ``exchange_rate`` are
    required.
    """

    __mapper_args__: ClassVar[dict[str, object]] = {
        "polymorphic_identity": "fx_rate_change",
    }

    source_currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        default=None,
    )
    target_currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        default=None,
    )
    exchange_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=10),
        nullable=True,
        default=None,
    )


__all__ = [
    "BuyOperation",
    "DividendOperation",
    "FeeOperation",
    "FxRateChangeOperation",
    "InterestOperation",
    "LimitBuyOperation",
    "LimitSellOperation",
    "Operation",
    "SellOperation",
    "StockSplitOperation",
    "TaxOperation",
    "TransferInOperation",
    "TransferOutOperation",
]
