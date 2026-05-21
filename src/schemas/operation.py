from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OperationBase(BaseModel):
    operation_type: str = Field(max_length=30)
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_amount: Decimal
    currency: str = Field(default="EUR", max_length=3)
    executed_at: datetime
    notes: str | None = None

    # Specific subclass fields
    limit_price: Decimal | None = None
    dividend_per_share: Decimal | None = None
    fee_category: str | None = Field(default=None, max_length=100)
    tax_category: str | None = Field(default=None, max_length=100)
    source_reference: str | None = Field(default=None, max_length=300)
    destination_reference: str | None = Field(default=None, max_length=300)
    split_ratio: Decimal | None = None
    source_currency: str | None = Field(default=None, max_length=3)
    target_currency: str | None = Field(default=None, max_length=3)
    exchange_rate: Decimal | None = None


class OperationCreate(OperationBase):
    position_id: int
    financial_account_id: int

    @model_validator(mode="after")
    def validate_polymorphic_fields(self) -> Self:
        op_type = self.operation_type

        if op_type in ("limit_buy", "limit_sell"):
            if self.limit_price is None:
                raise ValueError(f"limit_price is required for operation type '{op_type}'")
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

        return self


class OperationUpdate(BaseModel):
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    executed_at: datetime | None = None
    notes: str | None = None

    limit_price: Decimal | None = None
    dividend_per_share: Decimal | None = None
    fee_category: str | None = Field(default=None, max_length=100)
    tax_category: str | None = Field(default=None, max_length=100)
    source_reference: str | None = Field(default=None, max_length=300)
    destination_reference: str | None = Field(default=None, max_length=300)
    split_ratio: Decimal | None = None
    source_currency: str | None = Field(default=None, max_length=3)
    target_currency: str | None = Field(default=None, max_length=3)
    exchange_rate: Decimal | None = None


class OperationRead(OperationBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    position_id: int
    financial_account_id: int
    created_at: datetime
