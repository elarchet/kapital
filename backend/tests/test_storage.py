"""Storage backend unit tests (local filesystem + factory selection)."""

from __future__ import annotations

import pytest

from src.config import settings
from src.services.storage import (
    LocalStorageBackend,
    StorageError,
    StorageKeyNotFoundError,
    get_storage,
)


def test_local_backend_roundtrip(tmp_path):
    backend = LocalStorageBackend(tmp_path)

    assert not backend.exists("imports/1/abc")
    backend.put("imports/1/abc", b"col1,col2\n1,2\n", content_type="text/csv")
    assert backend.exists("imports/1/abc")
    assert backend.get("imports/1/abc") == b"col1,col2\n1,2\n"

    backend.delete("imports/1/abc")
    assert not backend.exists("imports/1/abc")
    # Deleting an absent key is a no-op, not an error.
    backend.delete("imports/1/abc")


def test_local_backend_overwrites_existing_key(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.put("k", b"v1")
    backend.put("k", b"v2")
    assert backend.get("k") == b"v2"


def test_local_backend_get_missing_key_raises(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(StorageKeyNotFoundError):
        backend.get("nope")


def test_local_backend_rejects_key_escaping_root(tmp_path):
    backend = LocalStorageBackend(tmp_path / "root")
    with pytest.raises(StorageError):
        backend.put("../outside", b"x")


def test_get_storage_factory_defaults_to_local(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "IMPORT_STORAGE_DIR", str(tmp_path))
    get_storage.cache_clear()
    try:
        backend = get_storage()
        assert isinstance(backend, LocalStorageBackend)
        assert get_storage() is backend  # memoized
    finally:
        get_storage.cache_clear()


def test_get_storage_factory_rejects_unknown_backend(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "ftp")
    get_storage.cache_clear()
    try:
        with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
            get_storage()
    finally:
        get_storage.cache_clear()
