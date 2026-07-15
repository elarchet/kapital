"""Pydantic schemas for Allocation (transaction split) APIs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.allocation import AllocationMethod


class AllocationLine(BaseModel):
    """A single split line targeting one position."""

    position_id: int
    method: AllocationMethod = AllocationMethod.PERCENTAGE
    value: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=300)


class AllocationSplitRequest(BaseModel):
    """Replace the allocations of a raw transaction with the given split lines."""

    raw_transaction_id: int
    lines: list[AllocationLine] = Field(min_length=1)


class AllocationRead(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    raw_transaction_id: int
    position_id: int
    method: AllocationMethod
    value: Decimal
    quantity: Decimal
    amount: Decimal
    currency: str
    is_default: bool
    notes: str | None = None
    created_at: datetime
