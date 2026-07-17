"""Imported-files feature over HTTP: storage on import, listing, content download."""

from __future__ import annotations

import hashlib
import json
from typing import cast

import pytest
from fastapi import status
from sqlmodel import select

from src.models import ImportedFile, Portfolio, RawTransaction, User
from src.services.import_service import import_portfolio_transactions
from src.services.import_storage import build_storage_key
from tests.factories import (
    ImportedFileFactory,
    PortfolioFactory,
    RawTransactionFactory,
    UserFactory,
)
from tests.test_api import get_auth_headers

CUSTOM_CONFIG = {
    "mappings": {
        "columns": {
            "operation_type": "Type",
            "executed_at": "Date",
            "name": "Asset",
            "total_amount": "Total",
            "currency": "Currency",
            "quantity": "Qty",
        },
        "type_mappings": {
            "buy": ["BUY"],
            "dividend": ["DIV"],
        },
    },
    "delimiter": ",",
    "decimal_separator": ".",
}

CSV_A = b"Type,Date,Asset,Total,Currency,Qty\nBUY,2026-01-10 10:00:00,Apple,150.0,USD,10\n"
CSV_B = b"Type,Date,Asset,Total,Currency,Qty\nDIV,2026-02-01 09:00:00,Apple,2.5,USD,\n"


@pytest.mark.asyncio
async def test_multifile_import_links_each_transaction_to_its_source_file(session):
    user = cast("User", UserFactory())
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    file_a = ImportedFileFactory(user=user)
    file_b = ImportedFileFactory(user=user)
    session.commit()

    await import_portfolio_transactions(
        db=session,
        portfolio_id=portfolio.id,
        user_id=user.id,
        file_content=[CSV_A, CSV_B],
        custom_schema_config=CUSTOM_CONFIG,
        imported_file_ids=[file_a.id, file_b.id],
    )

    txns = session.exec(select(RawTransaction).order_by(RawTransaction.executed_at)).all()
    assert [t.imported_file_id for t in txns] == [file_a.id, file_b.id]


def _import_files(client, headers, portfolio_id: int, files: list[tuple[str, bytes]]):
    return client.post(
        f"/api/v1/portfolios/{portfolio_id}/import",
        headers=headers,
        files=[("file", (name, content, "text/csv")) for name, content in files],
        data={"custom_schema_config": json.dumps(CUSTOM_CONFIG)},
    )


def test_import_endpoint_stores_files_and_dedups_reupload(client, session, storage):
    user = cast("User", UserFactory(email="storer@example.com"))
    portfolio = cast("Portfolio", PortfolioFactory(user=user))
    session.commit()
    headers = get_auth_headers(client, user.email)

    response = _import_files(client, headers, portfolio.id, [("t212.csv", CSV_A)])
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["raw_transactions_imported"] == 1

    records = session.exec(select(ImportedFile)).all()
    assert len(records) == 1
    record = records[0]
    assert record.filename == "t212.csv"
    assert record.sha256 == hashlib.sha256(CSV_A).hexdigest()
    assert storage.get(build_storage_key(user.id, record.sha256)) == CSV_A

    txn = session.exec(select(RawTransaction)).one()
    assert txn.imported_file_id == record.id

    # Re-uploading the identical file stores nothing new and imports nothing new.
    response = _import_files(client, headers, portfolio.id, [("t212-again.csv", CSV_A)])
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["skipped_duplicates"] == 1
    assert len(session.exec(select(ImportedFile)).all()) == 1


def test_list_imported_files_scoped_to_user_with_counts(client, session):
    user = cast("User", UserFactory(email="lister@example.com"))
    other = cast("User", UserFactory(email="other@example.com"))
    mine = ImportedFileFactory(user=user, filename="mine.csv")
    ImportedFileFactory(user=other, filename="theirs.csv")
    RawTransactionFactory(imported_file_id=None)  # legacy row, linked to nothing
    session.commit()
    RawTransactionFactory(imported_file_id=mine.id)
    RawTransactionFactory(imported_file_id=mine.id)
    session.commit()

    headers = get_auth_headers(client, user.email)
    response = client.get("/api/v1/imported-files/", headers=headers)

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert [f["filename"] for f in data] == ["mine.csv"]
    assert data[0]["transaction_count"] == 2
    assert data[0]["size_bytes"] == mine.size_bytes


def test_get_imported_file_content_and_ownership(client, session, storage):
    user = cast("User", UserFactory(email="downloader@example.com"))
    other = cast("User", UserFactory(email="intruder@example.com"))
    session.commit()
    sha256 = hashlib.sha256(CSV_A).hexdigest()
    key = build_storage_key(user.id, sha256)
    record = ImportedFileFactory(user=user, sha256=sha256, storage_key=key, filename="t212.csv")
    session.commit()
    storage.put(key, CSV_A, content_type="text/csv")

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/imported-files/{record.id}/content", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.content == CSV_A
    assert "t212.csv" in response.headers["content-disposition"]

    # Another user cannot see the file at all.
    other_headers = get_auth_headers(client, other.email)
    response = client.get(f"/api/v1/imported-files/{record.id}/content", headers=other_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_imported_file_content_missing_object_is_404(client, session):
    user = cast("User", UserFactory(email="ghost@example.com"))
    record = ImportedFileFactory(user=user, storage_key="imports/0/never-stored")
    session.commit()

    headers = get_auth_headers(client, user.email)
    response = client.get(f"/api/v1/imported-files/{record.id}/content", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "missing from object storage" in response.json()["detail"]


def test_delete_imported_file_keeps_transactions_but_unlinks_them(client, session, storage):
    user = cast("User", UserFactory(email="deleter@example.com"))
    record = ImportedFileFactory(user=user, storage_key="imports/9/deletable")
    session.commit()
    storage.put("imports/9/deletable", CSV_A)
    txn = RawTransactionFactory(imported_file_id=record.id)
    session.commit()

    headers = get_auth_headers(client, user.email)
    response = client.delete(f"/api/v1/imported-files/{record.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert session.exec(select(ImportedFile)).all() == []
    assert not storage.exists("imports/9/deletable")
    session.refresh(txn)
    assert txn.imported_file_id is None

    # And it no longer shows in the list.
    response = client.get("/api/v1/imported-files/", headers=headers)
    assert response.json() == []


def test_delete_imported_file_denied_for_other_user(client, session):
    owner = cast("User", UserFactory(email="owner@example.com"))
    intruder = cast("User", UserFactory(email="intruder2@example.com"))
    record = ImportedFileFactory(user=owner)
    session.commit()

    headers = get_auth_headers(client, intruder.email)
    response = client.delete(f"/api/v1/imported-files/{record.id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert len(session.exec(select(ImportedFile)).all()) == 1


def test_delete_imported_file_storage_outage_keeps_record(client, session):
    from src.main import app  # noqa: PLC0415
    from src.services.storage import StorageError, get_storage  # noqa: PLC0415

    class _BrokenDelete:
        def delete(self, key: str) -> None:
            raise StorageError("provider down")

    user = cast("User", UserFactory(email="outage@example.com"))
    record = ImportedFileFactory(user=user)
    session.commit()

    headers = get_auth_headers(client, user.email)
    app.dependency_overrides[get_storage] = _BrokenDelete
    response = client.delete(f"/api/v1/imported-files/{record.id}", headers=headers)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert len(session.exec(select(ImportedFile)).all()) == 1
