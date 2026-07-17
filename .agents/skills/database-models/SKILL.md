---
name: database-models
description: SQLModel database structures, schemas, and lifecycle rules.
---

# Database Models & Lifecycle Rules

This skill governs DB schemas, relationships, session management, and validation logic.

## 1. SQLModel & Strict Validation
- Define models using `SQLModel` with Pydantic configuration enforcing strict validation:
  ```python
  from sqlmodel import SQLModel, Field

  class UserBase(SQLModel):
      # Pydantic v2 configuration
      model_config = {
          "strict": True,
          "str_strip_whitespace": True
      }
  ```
- Declare relationships explicitly using `Relationship`.

## 2. Session Management & Dependency Injection
- Sessions are **synchronous** SQLModel `Session` objects — this project does not use async DB sessions. The session dependency lives in `backend/src/database.py`:
  ```python
  from collections.abc import Generator
  from sqlmodel import Session

  def get_session() -> Generator[Session]:
      """Dependency injection generator yielding a SQLModel Session."""
      with Session(engine) as session:
          yield session
  ```
- Avoid manual session opens. Inject the session into router endpoints via DI:
  ```python
  from typing import Annotated
  from fastapi import Depends
  from src.database import get_session

  # db: Annotated[Session, Depends(get_session)]
  ```

## 3. Bulk Operations & Performance
- **Batch Commits**: Avoid performing database commits (`db.commit()`) or database queries inside a loop during data ingestion (e.g., import wizard). This degrades database performance.
- **Transactional Consistency**: Perform all mutations within a single transaction block and execute a single batch `db.commit()` at the very end, wrapped in a `try/except` block with a `db.rollback()` on error.
- **In-Memory Caching**: Use dictionary caches to store references of existing entities (e.g., pre-fetched Positions, transaction IDs) during bulk operations to prevent N+1 select queries.

## 4. Database Migrations
- For detailed migration commands and lifecycle procedures, refer to [alembic_migrations.md](./references/alembic_migrations.md).
