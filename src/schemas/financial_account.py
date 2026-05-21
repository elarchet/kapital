from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FinancialAccountBase(BaseModel):
    name: str = Field(max_length=300)
    account_number: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="EUR", max_length=3)


class FinancialAccountCreate(FinancialAccountBase):
    institution_id: int


class FinancialAccountUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=300)
    account_number: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, max_length=3)
    institution_id: int | None = None


class FinancialAccountRead(FinancialAccountBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    institution_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
