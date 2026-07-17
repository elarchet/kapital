"""persist_import_files: per-user content dedup + storage-failure tolerance."""

from __future__ import annotations

import hashlib
from typing import cast

from sqlmodel import select

from src.models import ImportedFile, User
from src.services.import_storage import UploadedFileInfo, build_storage_key, persist_import_files
from src.services.storage import LocalStorageBackend, StorageError
from tests.factories import UserFactory

CSV = b"Type,Date,Total\nBUY,2026-01-10,150.0\n"


def _upload(filename: str = "export.csv", content: bytes = CSV) -> UploadedFileInfo:
    return UploadedFileInfo(filename=filename, content=content, content_type="text/csv")


def test_persist_stores_file_once_per_user(session, tmp_path):
    user = cast("User", UserFactory())
    session.commit()
    storage = LocalStorageBackend(tmp_path)

    first = persist_import_files(session, storage, user.id, [_upload()])
    # Same bytes again, even under another filename: row and object are reused.
    second = persist_import_files(session, storage, user.id, [_upload(filename="renamed.csv")])

    assert first[0] is not None
    assert second[0] is not None
    assert first[0].id == second[0].id
    assert second[0].filename == "export.csv"  # first-seen name is kept
    assert second[0].last_imported_at >= first[0].created_at

    sha256 = hashlib.sha256(CSV).hexdigest()
    records = session.exec(select(ImportedFile)).all()
    assert len(records) == 1
    assert records[0].sha256 == sha256
    assert records[0].size_bytes == len(CSV)
    assert storage.get(build_storage_key(user.id, sha256)) == CSV


def test_persist_same_content_two_users_kept_separate(session, tmp_path):
    user_a = cast("User", UserFactory())
    user_b = cast("User", UserFactory())
    session.commit()
    storage = LocalStorageBackend(tmp_path)

    persist_import_files(session, storage, user_a.id, [_upload()])
    persist_import_files(session, storage, user_b.id, [_upload()])

    records = session.exec(select(ImportedFile)).all()
    assert len(records) == 2
    assert {r.user_id for r in records} == {user_a.id, user_b.id}
    sha256 = hashlib.sha256(CSV).hexdigest()
    assert storage.exists(build_storage_key(user_a.id, sha256))
    assert storage.exists(build_storage_key(user_b.id, sha256))


def test_persist_dedups_within_one_batch(session, tmp_path):
    user = cast("User", UserFactory())
    session.commit()
    storage = LocalStorageBackend(tmp_path)

    records = persist_import_files(session, storage, user.id, [_upload(), _upload(filename="copy.csv")])

    assert records[0] is not None
    assert records[1] is not None
    assert records[0].id == records[1].id
    assert len(session.exec(select(ImportedFile)).all()) == 1


def test_persist_without_mark_imported_leaves_file_never_imported(session, tmp_path):
    user = cast("User", UserFactory())
    session.commit()
    storage = LocalStorageBackend(tmp_path)

    # Loading a file into the wizard stores it but doesn't count as an import.
    loaded = persist_import_files(session, storage, user.id, [_upload()], mark_imported=False)
    assert loaded[0] is not None
    assert loaded[0].last_imported_at is None
    sha256 = hashlib.sha256(CSV).hexdigest()
    assert storage.get(build_storage_key(user.id, sha256)) == CSV

    # Actually importing the same content stamps the existing row.
    imported = persist_import_files(session, storage, user.id, [_upload()])
    assert imported[0] is not None
    assert imported[0].id == loaded[0].id
    assert imported[0].last_imported_at is not None

    # Re-loading it later must not reset the imported timestamp.
    reloaded = persist_import_files(session, storage, user.id, [_upload()], mark_imported=False)
    assert reloaded[0] is not None
    assert reloaded[0].last_imported_at == imported[0].last_imported_at


class _BrokenStorage:
    """Storage stub whose writes always fail."""

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        raise StorageError("provider down")

    def get(self, key: str) -> bytes:
        raise StorageError("provider down")

    def exists(self, key: str) -> bool:
        return False

    def delete(self, key: str) -> None:
        return None


def test_persist_storage_failure_is_non_fatal(session, tmp_path):
    user = cast("User", UserFactory())
    session.commit()
    storage = LocalStorageBackend(tmp_path)

    records = persist_import_files(session, _BrokenStorage(), user.id, [_upload()])

    assert records == [None]
    assert session.exec(select(ImportedFile)).all() == []

    # A later retry with working storage stores the file normally.
    retry = persist_import_files(session, storage, user.id, [_upload()])
    assert retry[0] is not None
