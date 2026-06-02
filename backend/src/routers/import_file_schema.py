from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlmodel import Session

from src.auth import get_current_user
from src.crud import import_file_schema_crud
from src.database import get_session
from src.models import ImportFileSchema, User
from src.schemas import (
    ImportFileSchemaCreate,
    ImportFileSchemaRead,
)
from src.services.import_service import autodetect_schema

router = APIRouter(prefix="/import-file-schemas", tags=["import-file-schemas"])


@router.post(
    "/",
    response_model=ImportFileSchemaRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def create_import_file_schema(
    schema_in: ImportFileSchemaCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> ImportFileSchema:
    """Create a new import file schema template owned by the current user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    db_obj = ImportFileSchema(
        name=schema_in.name,
        is_public=False,
        delimiter=schema_in.delimiter,
        decimal_separator=schema_in.decimal_separator,
        mappings=schema_in.mappings,
        is_incomplete=schema_in.is_incomplete,
        user_id=current_user.id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get(
    "/",
    response_model=list[ImportFileSchemaRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def read_import_file_schemas(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    skip: Annotated[int, Query(ge=0, description="Number of schemas to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of schemas to return")] = 100,
) -> list[ImportFileSchema]:
    """Retrieve all available import file schemas (public + current user's)."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    return import_file_schema_crud.get_multi_by_user_or_public(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{schema_id}",
    response_model=ImportFileSchemaRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Import schema not found or not owned by user."},
    },
)
def read_import_file_schema(
    schema_id: Annotated[int, Path(description="The ID of the import file schema to retrieve")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> ImportFileSchema:
    """Retrieve details of a specific import file schema."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    schema = import_file_schema_crud.get_by_owner_or_public(
        db,
        id=schema_id,
        user_id=current_user.id,
    )
    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import schema not found or not owned by user.",
        )
    return schema


@router.delete(
    "/{schema_id}",
    response_model=ImportFileSchemaRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Import schema not found or deletion permission denied."},
    },
)
def delete_import_file_schema(
    schema_id: Annotated[int, Path(description="The ID of the import file schema to delete")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> ImportFileSchema:
    """Soft-delete an import file schema."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    schema = db.get(ImportFileSchema, schema_id)
    if not schema or schema.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import schema not found or you do not have permission to delete it.",
        )
    import_file_schema_crud.remove(db, id=schema_id)
    return schema


@router.post(
    "/detect",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def detect_schema_endpoint(
    headers: Annotated[list[str], Body(description="List of CSV column headers to match against existing schemas")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> dict[str, int | None]:
    """Auto-detect matching schema template from a list of CSV headers."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )
    best_id = autodetect_schema(db, headers=headers, user_id=current_user.id)
    return {"schema_id": best_id}
