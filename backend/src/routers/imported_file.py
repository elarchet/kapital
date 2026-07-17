"""Endpoints for a user's stored import files (store, list, download, delete).

Files are persisted the moment they are loaded into the import wizard (the
``POST /`` endpoint below), and again by the import endpoint which stamps
``last_imported_at`` (see ``services.import_storage``). Here users browse
their import history and fetch the original bytes to re-import a file
through the wizard without keeping the export around.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Path, Response, UploadFile, status
from sqlalchemy import func, update
from sqlmodel import Session, select

from src.auth import get_current_user
from src.database import get_session
from src.models import ImportedFile, RawTransaction, User
from src.schemas import ImportedFileRead
from src.services.import_storage import UploadedFileInfo, persist_import_files
from src.services.storage import StorageBackend, StorageError, StorageKeyNotFoundError, get_storage

router = APIRouter(prefix="/imported-files", tags=["imported-files"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    return current_user.id


@router.post(
    "/",
    response_model=list[ImportedFileRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Object storage is unavailable."},
    },
)
async def store_imported_files(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    file: Annotated[
        list[UploadFile],
        File(description="File(s) to persist as soon as they are loaded into the import wizard"),
    ],
) -> list[ImportedFileRead]:
    """Persist loaded files without importing them (``last_imported_at`` stays unset).

    Called by the wizard as soon as files are picked, so a file is kept even
    when the user never finishes the import (e.g. its mapping template is
    still incomplete). Re-uploading known content is a dedup no-op.
    """
    user_id = _require_user_id(current_user)
    contents = [await f.read() for f in file]
    records = persist_import_files(
        db,
        storage,
        user_id=user_id,
        files=[
            UploadedFileInfo(
                filename=f.filename or "import.csv",
                content=content,
                content_type=f.content_type,
            )
            for f, content in zip(file, contents, strict=True)
        ],
        mark_imported=False,
    )
    stored = [record for record in records if record is not None]
    if not stored and file:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Object storage is currently unavailable; the files were not stored.",
        )
    return [ImportedFileRead.model_validate(record) for record in stored]


@router.get(
    "/",
    response_model=list[ImportedFileRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def list_imported_files(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> list[ImportedFileRead]:
    """List the current user's stored import files, most recently used first."""
    user_id = _require_user_id(current_user)
    # Loaded-but-never-imported files have no last_imported_at; order them by
    # when they were first stored instead.
    last_used = func.coalesce(ImportedFile.last_imported_at, ImportedFile.created_at)
    statement = (
        select(ImportedFile, func.count(RawTransaction.id))
        .join(RawTransaction, RawTransaction.imported_file_id == ImportedFile.id, isouter=True)
        .where(ImportedFile.user_id == user_id)
        .group_by(ImportedFile.id)
        .order_by(last_used.desc())
    )
    rows = db.exec(statement).all()
    results = []
    for record, txn_count in rows:
        read = ImportedFileRead.model_validate(record)
        read.transaction_count = txn_count
        results.append(read)
    return results


@router.get(
    "/{file_id}/content",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Imported file not found or not owned by user."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Object storage is unavailable."},
    },
)
def get_imported_file_content(
    file_id: Annotated[int, Path(description="The ID of the imported file to download")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> Response:
    """Return the originally uploaded file bytes, e.g. to re-import them."""
    user_id = _require_user_id(current_user)
    record = db.get(ImportedFile, file_id)
    if not record or record.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imported file not found or not owned by user.",
        )

    try:
        content = storage.get(record.storage_key)
    except StorageKeyNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The stored file content is missing from object storage.",
        ) from err
    except StorageError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Object storage is currently unavailable.",
        ) from err

    return Response(
        content=content,
        media_type=record.content_type or "text/csv",
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Imported file not found or not owned by user."},
        status.HTTP_502_BAD_GATEWAY: {"description": "Object storage is unavailable."},
    },
)
def delete_imported_file(
    file_id: Annotated[int, Path(description="The ID of the imported file to delete")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> None:
    """Delete a stored file (object + record). Its imported transactions remain,
    with their source-file link cleared — re-import and future re-mapping become
    impossible for this file, which the frontend warns about before calling.
    """
    user_id = _require_user_id(current_user)
    record = db.get(ImportedFile, file_id)
    if not record or record.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imported file not found or not owned by user.",
        )

    # Remove the object first: if the provider is down we keep the record so
    # the user can retry, instead of leaking an orphaned object.
    try:
        storage.delete(record.storage_key)
    except StorageError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Object storage is currently unavailable; the file was not deleted.",
        ) from err

    db.exec(
        update(RawTransaction)
        .where(RawTransaction.imported_file_id == file_id)  # type: ignore[arg-type]
        .values(imported_file_id=None),
    )
    db.delete(record)
    db.commit()
