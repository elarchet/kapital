from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from src.models.fee import FeeType


class FeeBase(BaseModel):
    amount: Decimal
    currency: str
    fee_type: FeeType
    notes: str | None = None


class FeeCreate(FeeBase):
    pass


class FeeRead(FeeBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    raw_transaction_id: int
