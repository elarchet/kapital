"""Persist uploaded import files to object storage, deduplicated per user.

Files are content-addressed: the object key is ``imports/{user_id}/{sha256}``
and ``(user_id, sha256)`` is unique in the database, so re-uploading identical
content reuses the stored object and row. Storage outages are deliberately
non-fatal — the import proceeds and its transactions simply carry no source
file link (the same state as rows imported before file storage existed).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, NamedTuple

from sqlmodel import select

from src.models import ImportedFile
from src.services.storage import StorageError

if TYPE_CHECKING:
    from sqlmodel import Session

    from src.services.storage import StorageBackend

logger = logging.getLogger(__name__)


class UploadedFileInfo(NamedTuple):
    """One uploaded file's identity and raw bytes."""

    filename: str
    content: bytes
    content_type: str | None = None


def build_storage_key(user_id: int, sha256: str) -> str:
    """Content-addressed object key; the original filename lives in the DB only."""
    return f"imports/{user_id}/{sha256}"


def persist_import_files(
    db: Session,
    storage: StorageBackend,
    user_id: int,
    files: list[UploadedFileInfo],
) -> list[ImportedFile | None]:
    """Store each file once for this user and return records parallel to ``files``.

    A slot is ``None`` when the object store rejected that file — the caller
    keeps importing and the resulting transactions stay unlinked.
    """
    records: list[ImportedFile | None] = []
    now = datetime.now(UTC)

    for info in files:
        sha256 = hashlib.sha256(info.content).hexdigest()
        existing = db.exec(
            select(ImportedFile).where(
                ImportedFile.user_id == user_id,
                ImportedFile.sha256 == sha256,
            ),
        ).first()
        if existing:
            existing.last_imported_at = now
            db.add(existing)
            records.append(existing)
            continue

        storage_key = build_storage_key(user_id, sha256)
        try:
            storage.put(storage_key, info.content, content_type=info.content_type)
        except StorageError:
            logger.warning(
                "Object storage rejected import file %r for user %s; importing without provenance.",
                info.filename,
                user_id,
                exc_info=True,
            )
            records.append(None)
            continue

        record = ImportedFile(
            user_id=user_id,
            sha256=sha256,
            filename=info.filename,
            size_bytes=len(info.content),
            content_type=info.content_type,
            storage_key=storage_key,
            last_imported_at=now,
        )
        db.add(record)
        records.append(record)

    db.commit()
    for record in records:
        if record is not None:
            db.refresh(record)
    return records
