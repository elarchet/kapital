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

## 3. Centralized Exception Strategy
- Define a unified base exception (`KapitalError`) to manage domain-specific validation or business failures.
- Raise specific sub-exceptions in the services/logic layers and handle them using global FastAPI exception handlers to yield consistent, structured JSON responses:
  ```python
  from fastapi import FastAPI, Request
  from fastapi.responses import JSONResponse

  class KapitalError(Exception):
      pass

  # Register a global exception handler in the app initialization
  # @app.exception_handler(KapitalError)
  # async def error_handler(request: Request, exc: KapitalError):
  #     return JSONResponse(status_code=400, content={"detail": str(exc)})
  ```

## 4. Self-Documenting APIs
- Leverage FastAPI's automatic OpenAPI generation.
- Provide descriptive docstrings for all route functions.
- Explicitly define metadata in endpoints: `response_model`, `status_code`, `summary`, `description`, and parameter metadata (`Query`, `Path`) with description/examples to enrich the interactive `/docs` UI.
