from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlmodel import Session, select

from src.auth import get_current_user
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
    db_obj = Institution(**institution_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get("/", response_model=list[InstitutionRead])
def read_institutions(
    db: Annotated[Session, Depends(get_session)],
    skip: Annotated[int, Query(ge=0, description="Number of institutions to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of institutions to return")] = 100,
) -> list[Institution]:
    """Retrieve list of active master financial institutions."""
    statement = select(Institution).where(Institution.is_active == True).offset(skip).limit(limit)  # noqa: E712
    return list(db.exec(statement).all())


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
    institution = db.exec(
        select(Institution).where(Institution.id == institution_id, Institution.is_active),
    ).first()
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
    institution = db.exec(
        select(Institution).where(Institution.id == institution_id, Institution.is_active),
    ).first()
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    update_data = institution_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(institution, key, value)
    institution.updated_at = datetime.now(UTC)
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


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
    institution = db.exec(
        select(Institution).where(Institution.id == institution_id, Institution.is_active),
    ).first()
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found.",
        )
    institution.is_active = False
    institution.deleted_at = datetime.now(UTC)
    db.add(institution)
    db.commit()
    return institution
