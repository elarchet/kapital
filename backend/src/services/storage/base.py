"""Storage backend protocol and exceptions.

Callers only ever see :class:`StorageError` / :class:`StorageKeyNotFoundError`;
provider SDK errors (boto3, OSError) never leak past a backend.
"""

from __future__ import annotations

from typing import Protocol


class StorageError(Exception):
    """The storage provider failed to complete an operation."""


class StorageKeyNotFoundError(StorageError):
    """No object exists at the requested key."""


class StorageBackend(Protocol):
    """Minimal object-store interface shared by every provider."""

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Store ``data`` at ``key``, overwriting any existing object."""
        ...

    def get(self, key: str) -> bytes:
        """Return the object at ``key`` or raise ``StorageKeyNotFoundError``."""
        ...

    def exists(self, key: str) -> bool:
        """Return whether an object exists at ``key``."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object at ``key`` (no error if absent)."""
        ...
