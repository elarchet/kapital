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
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/kapital"

    # UI Component Marketplace Asset uploads
    UPLOAD_DIR: str = "static/uploads"
    ASSETS_BASE_URL: str = "http://localhost:8000/static/uploads"

    # Imported-file object storage ("local" filesystem or any "s3"-compatible
    # provider — Oracle Object Storage, AWS S3, MinIO, R2 — chosen by config).
    STORAGE_BACKEND: str = "local"
    IMPORT_STORAGE_DIR: str = "static/import_files"
    S3_ENDPOINT_URL: str | None = None
    S3_REGION: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None


settings = Settings()
