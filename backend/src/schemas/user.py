from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=320)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    public_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ThemeUpdate(BaseModel):
    theme: str


class UserPreferencesRead(BaseModel):
    theme: str
