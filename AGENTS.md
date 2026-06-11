# Project Constitution: Kapital

This document defines the core architecture, stack definitions, subagent matrix, and active skills registry.

---

## 1. Core Architecture & Tech Stack

### Constitutional Guidelines
- **Financial Expert**: Accuracy and security are non-negotiable. Use `Decimal` for all currency calculations. Never use floats.
- **Clean Decoupling**: All business/financial logic resides in the backend. The frontend only presents data via the REST API endpoints.
  - **Directory Rules**: Stateful operations (DB calls, external services) belong in `backend/src/services/`. Pure, stateless financial calculations (equations, interest models) belong in `backend/src/logic/`.
- **API Versioning**: All endpoints must be versioned under the `/api/v1/` prefix to prevent breaking changes.
- **Tailwind First**: All styling must use Tailwind CSS v4 utility classes. Declare theme variables once in `frontend/src/style.css`. `<style scoped>` blocks must remain empty or near-empty.
- **Tech Stack**: Vue.js, Tailwind CSS v4, FastAPI (`Annotated` dependencies), SQLModel + Alembic, Polars, Pydantic v2 (Strict), SQLite/PostgreSQL, `uv`, Modern Python.
- **Quality Control**: Automated hooks via `prek` running `ruff`, `ty`, `gitleaks`, and `commitizen`.

---

## 2. Specialized Subagents & Orchestration

To scale operations, the primary agent can invoke specialized subagents using the `/agent` command or the `invoke_subagent` tool.

| Subagent Role | Model Tier | Purpose |
| :--- | :--- | :--- |
| **`financial_expert`** | **Gemini 3.1 Pro** | Handles complex accounting calculations, tax rules, PnL equations, and Polars optimization logic. |
| **`frontend_designer`** | **Gemini 3.5 Flash** (Low) | Focused on crafting Vue components, implementing Tailwind CSS v4 styling rules, and layout design. |
| **`tester`** | **Gemini 3.5 Flash** (Low) | Responsible for writing comprehensive tests, setting up FactoryBoy mocks, and fixing test regressions. |
| **`researcher`** | **Gemini 3.5 Flash** (Low) | Scans documentation, runs codebase diagnostics, and searches web references. |
| **`architect_critic`** | **Gemini 3.1 Pro** | Hyper-critically assesses code architecture, weighs pros/cons, validates security/performance, and ensures scalability and future-proofing. |

---

## 3. Active Skills Registry

Skills are modular, on-demand instructions loaded only when required. They are stored in `.agents/skills/`.

- **[`financial_math`](file://./.agents/skills/financial_math/SKILL.md)**: Rules for Decimal arithmetic and Polars aggregations.
- **[`backend_api`](file://./.agents/skills/backend_api/SKILL.md)**: Design standards for FastAPI routes, REST endpoints, and dependency injection.
- **[`database_models`](file://./.agents/skills/database_models/SKILL.md)**: Standards for SQLModel models, database sessions, and Alembic migrations.
- **[`frontend_vue`](file://./.agents/skills/frontend_vue/SKILL.md)**: Rules for decoupled Vue components and Tailwind CSS v4 directives.
- **[`testing`](file://./.agents/skills/testing/SKILL.md)**: Pytest workflow, mock data generation rules, and coverage standards.
- **[`development_workflow`](file://./.agents/skills/development_workflow/SKILL.md)**: Git guidelines, Conventional Commits, file size budget, and verification procedures.

---

### Mandatory Pre-Flight / Pre-Commit Self-Check:
Before writing code or asking for commit approval, you MUST explicitly answer and document:
1. **Size Budget**: Do any new or modified files exceed 400 lines? If yes, split them now.
2. **Reusability**: Did you reuse existing sub-components or utilities instead of copy-pasting or building monolithic files?
3. **Structure**: Are your components placed in logical subfolders instead of a flat folder? If a feature has >3 components, did you place them in a dedicated subdirectory?
4. **Decoupled API**: Is all logic decoupled (frontend is representation/interaction only, business/financial logic is in the backend)?
