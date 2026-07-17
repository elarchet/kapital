from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    size_bytes: int
    sha256: str
    content_type: str | None = None
    created_at: datetime
    # None while the file has only been loaded into the wizard, never imported.
    last_imported_at: datetime | None = None
    # How many raw transactions this file produced (0 for template-only runs).
    transaction_count: int = 0
