from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session

from src.auth import get_current_user
from src.crud import institution_crud
from src.database import get_session
from src.models.institution import Institution
from src.schemas.institution import InstitutionCreate, InstitutionRead, InstitutionUpdate

# Apply authentication gate to all routes in this router at the router level
router = APIRouter(
    prefix="/institutions",
    tags=["institutions"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=InstitutionRead, status_code=status.HTTP_201_CREATED)
def create_institution(
    institution_in: InstitutionCreate,
    db: Annotated[Session, Depends(get_session)],
) -> Institution:
    """Create a new master financial institution (banks/brokers/exchanges)."""
    return institution_crud.create(db, obj_in=institution_in)


@router.get("/", response_model=list[InstitutionRead])
def read_institutions(
    db: Annotated[Session, Depends(get_session)],
    skip: Annotated[int, Query(ge=0, description="Number of institutions to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of institutions to return")] = 100,
) -> list[Institution]:
    """Retrieve list of active master financial institutions."""
    return institution_crud.get_multi(db, skip=skip, limit=limit)


@router.get(
    "/{institution_id}",
    response_model=InstitutionRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Institution not found."},
    },
)
def read_institution(
    institution_id: Annotated[int, Path(description="The ID of the institution to retrieve")],
    db: Annotated[Session, Depends(get_session)],
) -> Institution:
    """Retrieve details of a specific financial institution."""
    institution = institution_crud.get(db, id=institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    return institution


@router.put(
    "/{institution_id}",
    response_model=InstitutionRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Institution not found."},
    },
)
def update_institution(
    institution_id: Annotated[int, Path(description="The ID of the institution to update")],
    institution_in: InstitutionUpdate,
    db: Annotated[Session, Depends(get_session)],
) -> Institution:
    """Update details of a specific financial institution."""
    institution = institution_crud.get(db, id=institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    return institution_crud.update(db, db_obj=institution, obj_in=institution_in)


@router.delete(
    "/{institution_id}",
    response_model=InstitutionRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Institution not found."},
    },
)
def delete_institution(
    institution_id: Annotated[int, Path(description="The ID of the institution to delete")],
    db: Annotated[Session, Depends(get_session)],
) -> Institution:
    """Soft delete a specific financial institution."""
    institution = institution_crud.get(db, id=institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    institution_crud.remove(db, id=institution_id)
    return institution
