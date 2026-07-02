from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlmodel import Session, select

from src.auth import create_access_token, get_current_user
from src.database import get_session
from src.models.user import User
from src.schemas.user import ThemeUpdate, UserCreate, UserPreferencesRead, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


class OAuth2PasswordRequestFormEmail:
    """OAuth2 password request form that explicitly documents that the username is the email address."""

    def __init__(
        self,
        grant_type: Annotated[str | None, Form(pattern="password")] = None,
        username: Annotated[str, Form(description="Registered email address.")] = "",
        password: Annotated[str, Form(description="The user password.")] = "",
        scope: Annotated[str, Form(description="Space-separated scope string.")] = "",
        client_id: Annotated[str | None, Form(description="Optional client ID.")] = None,
        client_secret: Annotated[str | None, Form(description="Optional client secret.")] = None,
    ) -> None:
        self.grant_type = grant_type
        self.username = username
        self.password = password
        self.scopes = [s.strip() for s in scope.split()]
        self.client_id = client_id
        self.client_secret = client_secret


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A user with this email address already exists."},
    },
)
def register_user(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_session)],
) -> User:
    """Register a new user, checking that the email is unique."""
    existing_user = db.exec(select(User).where(User.email == user_in.email, User.is_active == True)).first()  # noqa: E712
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )
    db_user = User(email=user_in.email, hashed_password="")
    db_user.set_password(user_in.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post(
    "/token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Incorrect email or password."},
    },
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestFormEmail, Depends()],
    db: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    """Standard OAuth2 password flow login to obtain a JWT token.

    Note: The OAuth2 standard specifies the field name as `username`, but
    this API expects the registered `email` address in that field.
    """
    user = db.exec(select(User).where(User.email == form_data.username, User.is_active == True)).first()  # noqa: E712
    if not user or not user.verify_password(form_data.password):
        user = None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.public_id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserRead,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Could not validate credentials or user inactive."},
    },
)
def read_user_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Retrieve the profile of the currently logged in user."""
    return current_user


@router.get(
    "/preferences",
    response_model=UserPreferencesRead,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Current user record lacks a valid identifier."},
    },
)
def read_user_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Retrieve the current user's global theme preference."""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user record lacks a valid identifier.",
        )

    return {
        "theme": current_user.theme,
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

    return {
        "theme": current_user.theme,
    }
