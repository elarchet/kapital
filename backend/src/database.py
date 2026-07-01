from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from src.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    db_url,
    echo=False,
)


def init_db() -> None:
    """Initialize database and create all tables.

    Imports all models first to ensure they are registered with SQLAlchemy/SQLModel metadata.
    """
    # Import all models to register them on the metadata before calling create_all
    from src.models import SABase  # noqa: PLC0415

    SQLModel.metadata.create_all(engine)
    SABase.metadata.create_all(engine)


def get_session() -> Generator[Session]:
    """Dependency injection generator yielding a SQLModel Session."""
    with Session(engine) as session:
        yield session
