from __future__ import annotations

import logging

from sqlmodel import Session, create_engine, select

from src.config import settings
from src.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed() -> None:
    """Seed the database with the test user required by E2E tests."""
    logger.info("Connecting to database to seed test user: %s", settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        statement = select(User).where(User.email == "test@example.com")
        existing_user = session.exec(statement).first()
        if not existing_user:
            user = User(email="test@example.com")
            user.set_password("password123")
            session.add(user)
            session.commit()
            logger.info("Successfully seeded test@example.com user.")
        else:
            logger.info("test@example.com user already exists.")


if __name__ == "__main__":
    seed()
