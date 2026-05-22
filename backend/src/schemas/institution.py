from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InstitutionBase(BaseModel):
    name: str = Field(max_length=300)
    country: str | None = Field(default=None, max_length=2)
    website: str | None = Field(default=None, max_length=500)


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=300)
    country: str | None = Field(default=None, max_length=2)
    website: str | None = Field(default=None, max_length=500)


class InstitutionRead(InstitutionBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
