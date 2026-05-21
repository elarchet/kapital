from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode
from sqlmodel import Session, select

from src.config import settings
from src.database import get_session
from src.models.user import User

# Standard FastAPI password bearer login path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate a JWT access token containing the payload data."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": int(expire.timestamp())})
    return encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT access token.

    Returns the payload dictionary if valid, otherwise None.
    """
    try:
        payload = decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError, InvalidTokenError:
        return None
    return payload


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_session)],
) -> User:
    """FastAPI dependency to retrieve the currently logged in user context.

    Raises an HTTP 401 if credentials are invalid or user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise credentials_exception from None

    # Query user by public_id (masked internal primary keys)
    statement = select(User).where(User.public_id == user_uuid, User.is_active == True)  # noqa: E712
    user = db.exec(statement).first()

    if user is None:
        raise credentials_exception

    return user
