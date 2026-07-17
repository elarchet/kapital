"""Filesystem storage backend — dev and test default, no credentials needed."""

from __future__ import annotations

from pathlib import Path

from src.services.storage.base import StorageError, StorageKeyNotFoundError


class LocalStorageBackend:
    """Stores each object as a file at ``root / key``."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):
            msg = f"Storage key escapes the storage root: {key!r}"
            raise StorageError(msg)
        return path

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:  # noqa: ARG002 (protocol arg; meaningless on a filesystem)
        path = self._path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError as err:
            msg = f"Failed to write object {key!r}: {err}"
            raise StorageError(msg) from err

    def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as err:
            msg = f"No object stored at key {key!r}"
            raise StorageKeyNotFoundError(msg) from err
        except OSError as err:
            msg = f"Failed to read object {key!r}: {err}"
            raise StorageError(msg) from err

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as err:
            msg = f"Failed to delete object {key!r}: {err}"
            raise StorageError(msg) from err
