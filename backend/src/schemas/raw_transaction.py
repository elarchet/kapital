"""Pydantic schemas for RawTransaction ingestion and read APIs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.models.operation_enums import (
    ExpenseCategory,
    InterestType,
    OrderStatus,
    OrderType,
    PaymentMethod,
    RevenueCategory,
    TradeSide,
)
from src.schemas.fee import FeeCreate, FeeRead


class RawTransactionBase(BaseModel):
    operation_type: str = Field(max_length=30)
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    price_currency: str | None = Field(default=None, max_length=3)
    total_amount: Decimal
    currency: str = Field(default="EUR", max_length=3)
    executed_at: datetime
    notes: str | None = None

    # asset identifiers
    ticker: str | None = Field(default=None, max_length=20)
    isin: str | None = Field(default=None, max_length=12)
    name: str | None = Field(default=None, max_length=300)

    # trade-specific
    trade_side: TradeSide | None = None
    order_type: OrderType | None = None
    order_status: OrderStatus | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    execution_price: Decimal | None = None
    order_placed_at: datetime | None = None
    filled_at: datetime | None = None

    # category-specific
    dividend_per_share: Decimal | None = None
    fee_category: str | None = Field(default=None, max_length=100)
    tax_category: str | None = Field(default=None, max_length=100)
    source_reference: str | None = Field(default=None, max_length=300)
    destination_reference: str | None = Field(default=None, max_length=300)
    split_ratio: Decimal | None = None
    pre_split_quantity: Decimal | None = None
    source_currency: str | None = Field(default=None, max_length=3)
    target_currency: str | None = Field(default=None, max_length=3)
    exchange_rate: Decimal | None = None
    merchant_name: str | None = Field(default=None, max_length=200)
    merchant_category: str | None = Field(default=None, max_length=100)
    interest_type: InterestType | None = None
    expense_category: ExpenseCategory | None = None
    revenue_category: RevenueCategory | None = None
    payment_method: PaymentMethod | None = None


class RawTransactionCreate(RawTransactionBase):
    """Manual creation of a raw transaction plus an initial 100% allocation."""

    financial_account_id: int
    native_transaction_id: str | None = Field(default=None, max_length=100)
    fees: list[FeeCreate] | None = None
    # When provided, a default 100% allocation is created against this position.
    position_id: int | None = None


class RawTransactionRead(RawTransactionBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    financial_account_id: int
    dedup_key: str
    native_transaction_id: str | None = None
    is_auto_id: bool
    created_at: datetime
    fees: list[FeeRead] = []

    @computed_field
    @property
    def is_transaction_id_auto_generated(self) -> bool:
        return self.is_auto_id
