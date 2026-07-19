"""Pydantic schemas for Allocation (transaction split) APIs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.allocation import AllocationMethod


class AllocationLine(BaseModel):
    """A single split line targeting a position — directly or via a portfolio.

    Exactly one of ``position_id`` / ``portfolio_id`` must be set. With
    ``portfolio_id`` the service finds (or creates) the position matching the
    parent transaction's asset inside that portfolio, which is how a
    transaction is split across portfolios.
    """

    position_id: int | None = None
    portfolio_id: int | None = None
    method: AllocationMethod = AllocationMethod.PERCENTAGE
    value: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _exactly_one_target(self) -> AllocationLine:
        if (self.position_id is None) == (self.portfolio_id is None):
            msg = "Exactly one of position_id or portfolio_id must be set."
            raise ValueError(msg)
        return self


class AllocationSplitRequest(BaseModel):
    """Replace the allocations of a raw transaction with the given split lines."""

    lines: list[AllocationLine] = Field(min_length=1)


class AllocationRecombineRequest(BaseModel):
    """Collapse a transaction's splits back into a single 100% allocation."""

    position_id: int


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
