from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.operation import (
    ExpenseCategory,
    InterestType,
    OrderStatus,
    OrderType,
    PaymentMethod,
    RevenueCategory,
    TradeSide,
)
from src.schemas.fee import FeeCreate, FeeRead


class OperationBase(BaseModel):
    operation_type: str = Field(max_length=30)
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    price_currency: str | None = Field(default=None, max_length=3)
    total_amount: Decimal
    currency: str = Field(default="EUR", max_length=3)
    executed_at: datetime
    notes: str | None = None

    # Trade-specific fields
    trade_side: TradeSide | None = None
    order_type: OrderType | None = None
    order_status: OrderStatus | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    execution_price: Decimal | None = None
    order_placed_at: datetime | None = None
    filled_at: datetime | None = None

    # Subclass-specific fields
    dividend_per_share: Decimal | None = None
    fee_category: str | None = Field(default=None, max_length=100)
    tax_category: str | None = Field(default=None, max_length=100)
    source_reference: str | None = Field(default=None, max_length=300)
    destination_reference: str | None = Field(default=None, max_length=300)
    split_ratio: Decimal | None = None
    source_currency: str | None = Field(default=None, max_length=3)
    target_currency: str | None = Field(default=None, max_length=3)
    exchange_rate: Decimal | None = None
    transaction_id: str | None = Field(default=None, max_length=100)
    merchant_name: str | None = Field(default=None, max_length=200)
    merchant_category: str | None = Field(default=None, max_length=100)
    interest_type: InterestType | None = None

    # Everyday finance fields
    expense_category: ExpenseCategory | None = None
    revenue_category: RevenueCategory | None = None
    payment_method: PaymentMethod | None = None


class OperationCreate(OperationBase):
    position_id: int
    financial_account_id: int
    fees: list[FeeCreate] | None = None

    @model_validator(mode="after")
    def validate_polymorphic_fields(self) -> Self:
        op_type = self.operation_type

        if op_type == "trade":
            if self.trade_side is None:
                raise ValueError("trade_side is required for operation type 'trade'")
            if self.order_type is None:
                self.order_type = OrderType.MARKET
            if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.limit_price is None:
                raise ValueError(f"limit_price is required for order_type '{self.order_type}'")
            if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
                raise ValueError(f"stop_price is required for order_type '{self.order_type}'")
        elif op_type == "dividend":
            if self.dividend_per_share is None:
                raise ValueError("dividend_per_share is required for operation type 'dividend'")
        elif op_type == "fee":
            if self.fee_category is None:
                raise ValueError("fee_category is required for operation type 'fee'")
        elif op_type == "tax":
            if self.tax_category is None:
                raise ValueError("tax_category is required for operation type 'tax'")
        elif op_type == "transfer_in":
            if self.source_reference is None:
                raise ValueError("source_reference is required for operation type 'transfer_in'")
        elif op_type == "transfer_out":
            if self.destination_reference is None:
                raise ValueError("destination_reference is required for operation type 'transfer_out'")
        elif op_type == "stock_split":
            if self.split_ratio is None:
                raise ValueError("split_ratio is required for operation type 'stock_split'")
        elif op_type == "fx_rate_change" and any(
            val is None for val in (self.source_currency, self.target_currency, self.exchange_rate)
        ):
            raise ValueError(
                "source_currency, target_currency, and exchange_rate are all required for 'fx_rate_change'",
            )
        elif op_type == "interest" and self.interest_type is None:
            self.interest_type = InterestType.CASH_INTEREST
        elif op_type == "expense" and self.expense_category is None:
            self.expense_category = ExpenseCategory.OTHER
        elif op_type == "revenue" and self.revenue_category is None:
            self.revenue_category = RevenueCategory.OTHER

        return self


class OperationUpdate(BaseModel):
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    price_currency: str | None = Field(default=None, max_length=3)
    total_amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    executed_at: datetime | None = None
    notes: str | None = None

    # Trade fields
    trade_side: TradeSide | None = None
    order_type: OrderType | None = None
    order_status: OrderStatus | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    execution_price: Decimal | None = None
    order_placed_at: datetime | None = None
    filled_at: datetime | None = None

    # Subclass fields
    dividend_per_share: Decimal | None = None
    fee_category: str | None = Field(default=None, max_length=100)
    tax_category: str | None = Field(default=None, max_length=100)
    source_reference: str | None = Field(default=None, max_length=300)
    destination_reference: str | None = Field(default=None, max_length=300)
    split_ratio: Decimal | None = None
    source_currency: str | None = Field(default=None, max_length=3)
    target_currency: str | None = Field(default=None, max_length=3)
    exchange_rate: Decimal | None = None
    transaction_id: str | None = Field(default=None, max_length=100)
    merchant_name: str | None = Field(default=None, max_length=200)
    merchant_category: str | None = Field(default=None, max_length=100)
    interest_type: InterestType | None = None
    expense_category: ExpenseCategory | None = None
    revenue_category: RevenueCategory | None = None
    payment_method: PaymentMethod | None = None
    fees: list[FeeCreate] | None = None


class OperationRead(OperationBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    position_id: int
    financial_account_id: int
    created_at: datetime
    fees: list[FeeRead] = []
