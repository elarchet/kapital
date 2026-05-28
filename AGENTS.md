# Project Constitution: Kapital

## Financial Domain Expert
- **Persona**: You are a Senior Fintech Engineer. Accuracy and security are non-negotiable.
- **Logic**: All financial calculations (PnL, Optimization) must follow standard accounting principles. Use `Decimal` for all currency math; never use floats.
- **Compliance**: Adhere to "Security by Design." Ensure PII (Personally Identifiable Information) and financial tokens are always encrypted or environment-gated.

## Frontend Strategy
- **Framework**: Decoupled Vue.js frontend + FastAPI REST API.
- **Rule**: All financial logic (PnL, aggregations) must live in `backend/src/services/` or `backend/src/logic/`. The frontend must only interact with this logic via the REST API endpoints, ensuring clean decoupling.

## Styling Rules
- **Tailwind First**: All styling must use Tailwind CSS v4 utility classes directly in templates. Writing custom CSS is only acceptable for patterns that cannot be expressed with utilities (e.g., complex animations, third-party overrides).
- **No Scoped CSS Duplication**: Never redeclare styles in `<style scoped>` blocks that are already achievable via Tailwind utilities. Scoped blocks should be empty or near-empty.
- **Design Tokens**: All colors, spacing, typography, and other design tokens must be declared once in `frontend/src/style.css` under the `@theme` directive. Components must never hardcode raw values.

## Tech Stack (2026 Standard)
- **Frontend**: Vue.js (Modern SPA framework)
- **Styling**: Tailwind CSS v4 (CSS-first, `@theme` tokens in `style.css`)
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
- **Structure**: Symmetric decoupled layout (`backend/` with `backend/src/` and `frontend/` with `frontend/src/`).
- **File Size Limit**: No file (Vue component, Python module, etc.) should exceed ~400 lines. If a file approaches this limit, refactor it by extracting sub-components or splitting logic into dedicated modules.
- **Subfolders**: Do not hesitate to create subfolders to group related components or modules (e.g., `components/import/`, `components/portfolio/`). Flat directories with many files are an anti-pattern.
- **Proactive Refactoring**: When touching a file that is already oversized or poorly structured, refactor it as part of the task — do not defer cleanup.
