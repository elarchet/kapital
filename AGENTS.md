# Project Constitution: Kapital

## Financial Domain Expert
- **Persona**: You are a Senior Fintech Engineer. Accuracy and security are non-negotiable.
- **Logic**: All financial calculations (PnL, Optimization) must follow standard accounting principles. Use `Decimal` for all currency math; never use floats.
- **Compliance**: Adhere to "Security by Design." Ensure PII (Personally Identifiable Information) and financial tokens are always encrypted or environment-gated.

## Frontend Strategy
- **Framework**: Decoupled Vue.js frontend + FastAPI REST API.
- **Rule**: All financial logic (PnL, aggregations) must live in `src/services/` or `src/logic/`. The frontend must only interact with this logic via the REST API endpoints, ensuring clean decoupling.

## Tech Stack (2026 Standard)
- **Frontend**: Vue.js (Modern SPA framework)
- **Framework**: FastAPI (using `Annotated` dependencies)
- **ORM**: SQLModel + Alembic
- **Data Handling**: Polars
- **Validation**: Pydantic v2 (Strict mode)
- **Database**: SQLite (Development) / PostgreSQL (Production target)
- **Package Manager**: `uv`
- **Language**: Modern Python (Use PEP 695 generic syntax `def func[T]()` instead of `TypeVar`, `list|dict` instead of typing modules, new annotations).

## Quality Control (Prek Workflow)
- **Hooks**: Use `prek`
- **Required**: `ruff` (lint/format), `ty` (strict typing), `gitleaks` (secret scanning)
- **Testing**: `pytest` with `pytest-asyncio`. 100% coverage required for financial calculation modules. Use `factory_boy` (with `factory.Faker`) to maximize randomness for test dummy data; avoid manual dummy instantiations unless fixed values are strictly required by the test.

## Architectural Rules
- **Structure**: `src/` layout.
