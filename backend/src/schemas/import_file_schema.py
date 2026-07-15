from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ImportFileSchemaBase(BaseModel):
    name: str
    is_public: bool = False
    delimiter: str = ","
    decimal_separator: str = "."
    mappings: str = "{}"
    is_incomplete: bool = False
    institution_key: str = "custom"
    institution_id: int | None = None


class ImportFileSchemaCreate(ImportFileSchemaBase):
    pass


class ImportFileSchemaUpdate(BaseModel):
    name: str | None = None
    is_public: bool | None = None
    delimiter: str | None = None
    decimal_separator: str | None = None
    mappings: str | None = None
    is_incomplete: bool | None = None
    institution_key: str | None = None
    institution_id: int | None = None


class ImportFileSchemaRead(ImportFileSchemaBase):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: int
    user_id: int | None = None
