"""Endpoints for a user's stored import files (list + raw content download).

Files are persisted by the import endpoint (see ``services.import_storage``);
here users browse their import history and fetch the original bytes to
re-import a file through the wizard without keeping the export around.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import func, update
from sqlmodel import Session, select

from src.auth import get_current_user
from src.database import get_session
from src.models import ImportedFile, RawTransaction, User
from src.schemas import ImportedFileRead
from src.services.storage import StorageBackend, StorageError, StorageKeyNotFoundError, get_storage

router = APIRouter(prefix="/imported-files", tags=["imported-files"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    return current_user.id


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
    statement = (
        select(ImportedFile, func.count(RawTransaction.id))
        .join(RawTransaction, RawTransaction.imported_file_id == ImportedFile.id, isouter=True)
        .where(ImportedFile.user_id == user_id)
        .group_by(ImportedFile.id)
        .order_by(ImportedFile.last_imported_at.desc())  # type: ignore[attr-defined]
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
