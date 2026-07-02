"""Schemas for cost basis API responses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SplitEventRead(BaseModel):
    """A single split event record for audit display."""

    model_config = ConfigDict(strict=True, from_attributes=True)

    executed_at: datetime
    split_ratio: Decimal
    pre_split_quantity: Decimal | None = None
    post_split_quantity: Decimal | None = None


class CostBasisRead(BaseModel):
    """Split-adjusted cost basis for a position.

    ``total_amount`` of individual trades is NEVER adjusted (real cash flow).
    ``avg_cost_basis`` and ``total_shares`` reflect split-adjusted values.

    Tax-forward note:
        This schema returns weighted-average cost basis. A future endpoint
        can return FIFO lot details by extending ``split_events`` with per-lot
        acquisition records from the adjusted operations DataFrame.
    """

    model_config = ConfigDict(strict=True)

    position_id: int
    avg_cost_basis: Decimal
    total_invested: Decimal
    total_shares: Decimal
    split_events: list[SplitEventRead] = []
