from __future__ import annotations

import pathlib
import shutil
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlmodel import Session

from src.auth import get_current_user
from src.config import settings
from src.crud import ui_component_override_crud, ui_component_variant_crud
from src.database import get_session
from src.models import User
from src.models.ui_marketplace import UIComponentOverride, UIComponentVariant
from src.schemas import (
    ThemeUpdate,
    UIComponentOverrideCreate,
    UIComponentVariantCreate,
    UIComponentVariantRead,
    UserPreferencesRead,
)

router = APIRouter(prefix="/user/preferences", tags=["ui-marketplace"])


@router.get(
    "/",
    response_model=UserPreferencesRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def read_user_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> dict:
    """Retrieve the current user's global theme and all active component overrides."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    overrides = ui_component_override_crud.get_all_by_user(db, user_id=current_user.id)
    overrides_dict = {}
    for override in overrides:
        variant = ui_component_variant_crud.get(db, override.variant_id)
        if variant and variant.is_active:
            overrides_dict[override.component_key] = variant

    return {
        "theme": current_user.theme,
        "overrides": overrides_dict,
    }


@router.put(
    "/theme",
    response_model=UserPreferencesRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def update_user_theme(
    theme_in: ThemeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> dict:
    """Update the current user's global theme selection."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    current_user.theme = theme_in.theme
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # Resolve overrides for the return model
    overrides = ui_component_override_crud.get_all_by_user(db, user_id=current_user.id)
    overrides_dict = {}
    for override in overrides:
        variant = ui_component_variant_crud.get(db, override.variant_id)
        if variant and variant.is_active:
            overrides_dict[override.component_key] = variant

    return {
        "theme": current_user.theme,
        "overrides": overrides_dict,
    }


@router.get(
    "/variants",
    response_model=list[UIComponentVariantRead],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def read_component_variants(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    component_key: Annotated[str | None, Query(description="Filter by specific component key")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[UIComponentVariant]:
    """Retrieve all available component variants (public + user-owned)."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    variants = ui_component_variant_crud.get_multi_by_user_or_public(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    if component_key:
        variants = [v for v in variants if v.component_key == component_key]

    return variants


@router.post(
    "/variants",
    response_model=UIComponentVariantRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def create_component_variant(
    variant_in: UIComponentVariantCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> UIComponentVariant:
    """Register a custom component variant owned by the current user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    db_obj = UIComponentVariant(
        component_key=variant_in.component_key,
        name=variant_in.name,
        description=variant_in.description,
        asset_url=variant_in.asset_url,
        is_public=False,
        user_id=current_user.id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete(
    "/variants/{variant_id}",
    response_model=UIComponentVariantRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Variant not found or permission denied."},
    },
)
def delete_component_variant(
    variant_id: Annotated[int, Path(description="The ID of the component variant to delete")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> UIComponentVariant:
    """Soft-delete a user-owned custom component variant."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    variant = db.get(UIComponentVariant, variant_id)
    if not variant or variant.user_id != current_user.id or not variant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component variant not found or you do not have permission to delete it.",
        )

    ui_component_variant_crud.remove(db, id=variant_id)
    return variant


@router.post(
    "/components",
    response_model=UIComponentVariantRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Custom variant not found or not accessible."},
    },
)
def set_component_override(
    override_in: UIComponentOverrideCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> UIComponentVariant:
    """Create or update a custom component override for the current user."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    # Verify target variant exists and is accessible
    variant = ui_component_variant_crud.get_by_owner_or_public(
        db,
        id=override_in.variant_id,
        user_id=current_user.id,
    )
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component variant not found or not accessible.",
        )

    # Check for existing override
    existing = ui_component_override_crud.get_by_user_and_key(
        db,
        user_id=current_user.id,
        component_key=override_in.component_key,
    )
    if existing:
        existing.variant_id = override_in.variant_id
        db.add(existing)
        db.commit()
        db.refresh(existing)
    else:
        new_override = UIComponentOverride(
            user_id=current_user.id,
            component_key=override_in.component_key,
            variant_id=override_in.variant_id,
        )
        db.add(new_override)
        db.commit()

    return variant


@router.delete(
    "/components/{component_key}",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
        status.HTTP_404_NOT_FOUND: {"description": "Override not found."},
    },
)
def revert_component_override(
    component_key: Annotated[str, Path(description="The component key to revert to default")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> dict:
    """Remove a custom component override, reverting the component to the default fallback."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    existing = ui_component_override_crud.get_by_user_and_key(
        db,
        user_id=current_user.id,
        component_key=component_key,
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active component override found for key '{component_key}'.",
        )

    ui_component_override_crud.remove(db, id=existing.id)
    return {"message": f"Successfully reverted '{component_key}' to default fallback."}


@router.post(
    "/upload",
    response_model=UIComponentVariantRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "User identifier missing or validation failed.",
        },
    },
)
def upload_component_variant(
    component_key: Annotated[str, Form(description="The component key")],
    name: Annotated[str, Form(description="The display name of this variant")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    file: Annotated[UploadFile, File(description="ESM bundle JS file")],
    description: Annotated[str | None, Form(description="Optional variant description")] = None,
) -> UIComponentVariant:
    """Upload a custom compiled ESM bundle JS file and register it as a variant."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    # Validate file extension
    if not file.filename or not file.filename.endswith(".js"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only compiled ESM bundles (.js files) are accepted.",
        )

    # Whitelist component keys to prevent path traversal or unregistered overrides
    valid_keys = {
        "sidebar",
        "custom-dropdown",
        "base-confirm-modal",
        "add-position-button",
        "create-position-modal",
        "right-panel-drawer",
    }
    if component_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component key. Must be one of {sorted(valid_keys)}",
        )

    # Validate file size (limit: 2 MB)
    max_file_size = 2 * 1024 * 1024  # 2MB
    try:
        content = file.file.read(max_file_size + 1)
        if len(content) > max_file_size:
            raise HTTPException(  # noqa: TRY301
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the 2 MB limit.",
            )
        # Reset file pointer for subsequent copy
        file.file.seek(0)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file for size validation: {e!s}",
        ) from e

    # Ensure upload directory exists
    pathlib.Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # Generate safe unique filename
    safe_filename = f"{component_key}_{uuid.uuid4().hex}.js"
    file_path = pathlib.Path(settings.UPLOAD_DIR) / safe_filename

    # Save file to upload directory
    try:
        with pathlib.Path(file_path).open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file to local disk: {e!s}",
        ) from e

    # Build asset URL
    asset_url = f"{settings.ASSETS_BASE_URL}/{safe_filename}"

    # Save variant DB object
    db_obj = UIComponentVariant(
        component_key=component_key,
        name=name,
        description=description,
        asset_url=asset_url,
        is_public=False,
        user_id=current_user.id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
