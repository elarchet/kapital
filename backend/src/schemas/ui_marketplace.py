from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UIComponentVariantBase(BaseModel):
    component_key: str
    name: str
    description: str = ""
    asset_url: str
    is_public: bool = False


class UIComponentVariantCreate(UIComponentVariantBase):
    pass


class UIComponentVariantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    asset_url: str | None = None
    is_public: bool | None = None


class UIComponentVariantRead(UIComponentVariantBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    user_id: int | None = None


class UIComponentOverrideBase(BaseModel):
    component_key: str
    variant_id: int


class UIComponentOverrideCreate(UIComponentOverrideBase):
    pass


class UIComponentOverrideRead(UIComponentOverrideBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    user_id: int


class ThemeUpdate(BaseModel):
    theme: str


class UserPreferencesRead(BaseModel):
    theme: str
    overrides: dict[str, UIComponentVariantRead | None]
