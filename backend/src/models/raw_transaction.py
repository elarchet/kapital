"""RawTransaction model — the immutable, idempotent ingested record.

A ``RawTransaction`` is the raw imported transaction exactly as it arrived from
an institution's export, decoupled from any portfolio or position. User-defined
portfolio segmentation lives in :class:`~src.models.allocation.Allocation`
records that reference a raw transaction as their parent (1-to-Many).

Idempotency is enforced by ``(financial_account_id, dedup_key)`` uniqueness:
``dedup_key`` is either the source's native transaction id or a deterministic
``auto-<sha256>`` hash derived from the row (see ``logic.idempotency``).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from src.models.base import SoftDeleteMixin, TimestampMixin
from src.models.operation_enums import (
    ExpenseCategory,
    InterestType,
    OrderStatus,
    OrderType,
    PaymentMethod,
    RevenueCategory,
    TradeSide,
)

if TYPE_CHECKING:
    from src.models.allocation import Allocation
    from src.models.fee import Fee
    from src.models.financial_account import FinancialAccount


class RawTransaction(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """An immutable transaction as ingested from an institution export."""

    __tablename__ = "raw_transaction"
    __table_args__ = (UniqueConstraint("financial_account_id", "dedup_key", name="uq_raw_txn_account_dedup"),)

    id: int | None = Field(default=None, primary_key=True)
    operation_type: str = Field(nullable=False, max_length=30, index=True)

    # -- idempotency & provenance ---------------------------------------------
    dedup_key: str = Field(nullable=False, max_length=100, index=True)
    native_transaction_id: str | None = Field(default=None, max_length=100, index=True)
    is_auto_id: bool = Field(default=False, nullable=False)
    raw_payload: str | None = Field(default=None)  # original row serialized as JSON

    # -- asset identifiers -----------------------------------------------------
    ticker: str | None = Field(default=None, max_length=20, index=True)
    isin: str | None = Field(default=None, max_length=12, index=True)
    name: str | None = Field(default=None, max_length=300)

    # -- core financials -------------------------------------------------------
    quantity: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    unit_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    price_currency: str | None = Field(default=None, max_length=3)
    total_amount: Decimal = Field(nullable=False, max_digits=20, decimal_places=8)
    currency: str = Field(default="EUR", nullable=False, max_length=3)
    executed_at: datetime = Field(nullable=False, index=True)
    notes: str | None = Field(default=None)
    exchange_rate: Decimal | None = Field(default=None, max_digits=20, decimal_places=10)
    source_currency: str | None = Field(default=None, max_length=3)
    target_currency: str | None = Field(default=None, max_length=3)

    # -- trade-specific --------------------------------------------------------
    trade_side: TradeSide | None = Field(default=None)
    order_type: OrderType | None = Field(default=None)
    order_status: OrderStatus | None = Field(default=None)
    limit_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    stop_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    execution_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    order_placed_at: datetime | None = Field(default=None)
    filled_at: datetime | None = Field(default=None)

    # -- category-specific -----------------------------------------------------
    dividend_per_share: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    fee_category: str | None = Field(default=None, max_length=100)
    tax_category: str | None = Field(default=None, max_length=100)
    source_reference: str | None = Field(default=None, max_length=300)
    destination_reference: str | None = Field(default=None, max_length=300)
    split_ratio: Decimal | None = Field(default=None, max_digits=12, decimal_places=6)
    pre_split_quantity: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    merchant_name: str | None = Field(default=None, max_length=200)
    merchant_category: str | None = Field(default=None, max_length=100)
    interest_type: InterestType | None = Field(default=None)
    expense_category: ExpenseCategory | None = Field(default=None)
    revenue_category: RevenueCategory | None = Field(default=None)
    payment_method: PaymentMethod | None = Field(default=None)

    # -- foreign keys ----------------------------------------------------------
    financial_account_id: int = Field(
        foreign_key="financial_account.id",
        nullable=False,
        index=True,
    )
    # Source file provenance; NULL for rows imported before files were stored.
    imported_file_id: int | None = Field(
        default=None,
        foreign_key="imported_file.id",
        index=True,
    )

    # -- relationships ---------------------------------------------------------
    financial_account: "FinancialAccount" = Relationship(back_populates="raw_transactions")
    fees: list["Fee"] = Relationship(
        back_populates="raw_transaction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
    allocations: list["Allocation"] = Relationship(
        back_populates="raw_transaction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
