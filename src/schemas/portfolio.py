from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortfolioBase(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class PortfolioRead(PortfolioBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
