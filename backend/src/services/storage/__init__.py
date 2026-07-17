"""Provider-agnostic object storage for imported files.

``get_storage()`` returns the backend selected by ``settings.STORAGE_BACKEND``:
``"local"`` (filesystem, dev/tests) or ``"s3"`` (any S3-compatible endpoint —
Oracle Object Storage, AWS S3, MinIO, R2 — switching provider is config only).
Routers inject it with ``Depends(get_storage)`` so tests can override it.
"""

from __future__ import annotations

from functools import lru_cache

from src.config import settings
from src.services.storage.base import (
    StorageBackend,
    StorageError,
    StorageKeyNotFoundError,
)
from src.services.storage.local import LocalStorageBackend

__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
    "StorageError",
    "StorageKeyNotFoundError",
    "get_storage",
]


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """Build (once) the storage backend selected by settings."""
    backend = settings.STORAGE_BACKEND.strip().lower()
    if backend == "s3":
        from src.services.storage.s3 import S3StorageBackend  # noqa: PLC0415 (lazy: boto3 only in s3 mode)

        return S3StorageBackend(
            endpoint_url=settings.S3_ENDPOINT_URL,
            region=settings.S3_REGION,
            bucket=settings.S3_BUCKET,
            access_key_id=settings.S3_ACCESS_KEY_ID,
            secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
    if backend == "local":
        return LocalStorageBackend(settings.IMPORT_STORAGE_DIR)
    msg = f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r} (expected 'local' or 's3')."
    raise ValueError(msg)
