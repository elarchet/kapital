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
- Always use async database sessions for all operations when integrated with FastAPI.
- Avoid manual session opens. Use router Dependency Injection to manage session lifecycles:
  ```python
  from sqlalchemy.ext.asyncio import AsyncSession
  from typing import Annotated
  from fastapi import Depends

  # Inject the session into router endpoints
  # db: Annotated[AsyncSession, Depends(get_db_session)]
  ```

## 3. Bulk Operations & Performance
- **Batch Commits**: Avoid performing database commits (`db.commit()`) or database queries inside a loop during data ingestion (e.g., import wizard). This degrades database performance.
- **Transactional Consistency**: Perform all mutations within a single transaction block and execute a single batch `db.commit()` at the very end, wrapped in a `try/except` block with a `db.rollback()` on error.
- **In-Memory Caching**: Use dictionary caches to store references of existing entities (e.g., pre-fetched Positions, transaction IDs) during bulk operations to prevent N+1 select queries.

## 4. Database Migrations
- For detailed migration commands and lifecycle procedures, refer to [alembic_migrations.md](file://./references/alembic_migrations.md).
