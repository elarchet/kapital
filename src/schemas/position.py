from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.models.position import AssetType


class PositionBase(BaseModel):
    asset_type: AssetType
    ticker: str | None = Field(default=None, max_length=20)
    name: str = Field(max_length=300)
    isin: str | None = Field(default=None, max_length=12)
    quantity: Decimal = Field(default=Decimal("0.0"))
    currency: str = Field(default="EUR", max_length=3)


class PositionCreate(PositionBase):
    portfolio_id: int


class PositionUpdate(BaseModel):
    asset_type: AssetType | None = None
    ticker: str | None = Field(default=None, max_length=20)
    name: str | None = Field(default=None, max_length=300)
    isin: str | None = Field(default=None, max_length=12)
    quantity: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    portfolio_id: int | None = None


class PositionRead(PositionBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    portfolio_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
