from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, environment-gated."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Security & Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./kapital.db"

    # UI Component Marketplace Asset uploads
    UPLOAD_DIR: str = "static/uploads"
    ASSETS_BASE_URL: str = "http://localhost:8000/static/uploads"


settings = Settings()
