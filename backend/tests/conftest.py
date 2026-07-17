from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlmodel import Session, SQLModel

from src.database import get_session
from src.main import app
from src.models import SABase
from src.services.storage import LocalStorageBackend, get_storage
from tests.factories import set_factory_session


@pytest.fixture(name="engine")
def fixture_engine():
    """PostgreSQL engine with all tables created, isolated per test."""
    db_url = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/kapital_test")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Auto-create the test database if it doesn't exist
    base_url, db_name = db_url.rsplit("/", 1)
    temp_url = f"{base_url}/postgres"
    temp_eng = create_engine(temp_url, isolation_level="AUTOCOMMIT")
    with temp_eng.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name},
        ).scalar()
        if not exists:
            if not re.match(r"^[a-zA-Z0-9_]+$", db_name):
                raise ValueError(f"Invalid test database name: {db_name}")
            conn.execute(text(f"CREATE DATABASE {db_name}"))
    temp_eng.dispose()

    eng = create_engine(db_url, echo=False)

    # Ensure clean database tables (including custom PostgreSQL types/enums)
    with eng.connect() as conn, conn.begin():
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        # Grant privileges back to public
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))

    SQLModel.metadata.create_all(eng)
    SABase.metadata.create_all(eng)

    yield eng

    # Cleanup after test to prevent schema pollution
    SQLModel.metadata.drop_all(eng)
    SABase.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(name="session")
def fixture_session(engine):
    """Yield a fresh session per test."""
    with Session(engine) as s:
        set_factory_session(s)
        yield s
        set_factory_session(None)


@pytest.fixture(name="storage")
def fixture_storage(tmp_path):
    """Isolated filesystem object store for a single test."""
    return LocalStorageBackend(tmp_path / "object_store")


@pytest.fixture(name="client")
def fixture_client(session, storage):
    """Yield a TestClient with database session and object storage overridden."""

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
