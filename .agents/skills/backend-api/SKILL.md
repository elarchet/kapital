---
name: backend-api
description: API design standards for FastAPI routers, REST endpoints, and dependency injection.
---

# Backend API Design Standards

This skill governs the structure and endpoints of the FastAPI application.

## 1. FastAPI Decoupling & Versioning
- Keep business logic decoupled from FastAPI routers. Put stateful orchestrations in `backend/src/services/` and stateless math in `backend/src/logic/`.
- Router endpoints must only handle parsing/validation, calling services, and returning responses.
- Version all endpoints under `/api/v1/`.

## 2. Validation & Serialization
- Use Pydantic schemas for request and response models.
- Ensure all models strictly type their fields.
- Avoid passing raw database models directly to/from endpoints if serialization properties differ.

## 3. Exception Strategy
- **Current pattern**: routers raise FastAPI's `HTTPException` directly with an explicit `status_code` and `detail` (see `backend/src/routers/auth.py`):
  ```python
  from fastapi import HTTPException, status

  raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid credentials",
  )
  ```
- There is **no** `KapitalError` base exception or global exception handler today — do not import one.
- **Aspirational** (only if a task explicitly calls for it): a unified `KapitalError` base plus `@app.exception_handler` registration would let services/logic raise domain exceptions without importing FastAPI. Introduce it deliberately, not by assuming it already exists.

## 4. Self-Documenting APIs
- Leverage FastAPI's automatic OpenAPI generation.
- Provide descriptive docstrings for all route functions.
- Explicitly define metadata in endpoints: `response_model`, `status_code`, `summary`, `description`, and parameter metadata (`Query`, `Path`) with description/examples to enrich the interactive `/docs` UI.
