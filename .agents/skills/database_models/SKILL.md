---
name: database_models
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

## 3. Database Migrations
- For detailed migration commands and lifecycle procedures, refer to [alembic_migrations.md](file://./references/alembic_migrations.md).
