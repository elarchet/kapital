# Project Constitution: Kapital

This document defines the core architecture, stack definitions, subagent matrix, and active skills registry.

---

## 1. Core Architecture & Tech Stack

### Constitutional Guidelines
- **Financial Expert**: Accuracy and security are non-negotiable. Use `Decimal` for all currency calculations. Never use floats.
- **Clean Decoupling**: All business/financial logic resides in the backend. The frontend only presents data via the REST API endpoints.
  - **Directory Rules**: Stateful operations (DB calls, external services) belong in `backend/src/services/`. Pure, stateless financial calculations (equations, interest models) belong in `backend/src/logic/`.
- **API Versioning**: All endpoints must be versioned under the `/api/v1/` prefix to prevent breaking changes.
- **No Retro-Compatibility Constraints**: During beta development, backward-compatibility is not required. APIs, endpoints, and schemas can be aggressively cleaned up, simplified, or broken to optimize the architecture, without carrying legacy parameters or adapter layers.
- **Tailwind First**: All styling must use Tailwind CSS v4 utility classes. Declare theme variables once in `frontend/src/style.css`. `<style scoped>` blocks must remain empty or near-empty.
- **Tech Stack**: Vue.js, Tailwind CSS v4, Playwright, FastAPI (`Annotated` dependencies), SQLModel + Alembic, Polars, Pydantic v2 (Strict), SQLite/PostgreSQL, `uv`, Modern Python.
- **Bulk Mutations & Performance**: Optimize bulk updates or imports by caching database lookups in-memory and using a single batch `db.commit()` in a try-except-rollback block at the service layer, avoiding N+1 queries and loop commits.
- **Defensive Rendering**: Defensively use optional chaining (`?.`) when displaying dynamic rows, custom templates, or mapped fields to prevent UI crashes if some attributes are missing.
- **Ponytail / Minimalist Architecture**: Enforce YAGNI (You Ain't Gonna Need It) principles strictly. Avoid over-engineering, redundant file structures, and unnecessary abstractions. Consolidate logic into fewer, well-scoped files and prioritize standard library/native solutions as detailed in [.agents/.rules/ponytail.md](file:///home/etien/dev/perso/kapital/.agents/.rules/ponytail.md).
- **Strict Commit Protocols**: Never perform git commits or push changes to the repository without explicit consent from the user. Refer to and strictly follow the [git-commit](file:///home/etien/dev/perso/kapital/.agents/skills/git-commit/SKILL.md) skill.
- **Quality Control**: Automated hooks via `prek` running `ruff`, `ty`, `gitleaks`, and `commitizen`.

---

## 2. Specialized Subagents & Orchestration

To scale operations, the primary agent can invoke specialized subagents using the `/agent` command or the `invoke_subagent` tool.

| Subagent Role | Model Tier | Purpose |
| :--- | :--- | :--- |
| **`financial_expert`** | **Gemini 3.1 Pro** | Handles complex accounting calculations, tax rules, PnL equations, and Polars optimization logic. |
| **`frontend_designer`** | **Gemini 3.5 Flash** (Low) | Focused on crafting functional Vue components, implementing Tailwind CSS v4 styling rules, and layout design strictly following the contracts and tokens defined by the architect. |
| **`frontend_architect`** | **Claude Sonnet 4.6** | Responsible for the design system architecture, strict component contracts (API/Props definitions for the marketplace), and runtime theming engines. |
| **`tester`** | **Gemini 3.5 Flash** (Low) | Responsible for writing comprehensive tests, setting up FactoryBoy mocks, and fixing test regressions. |
| **`architect_critic`** | **Claude Opus 4.6** | Hyper-critically assesses code architecture, weighs pros/cons, validates security/performance, and ensures scalability and future-proofing. |

### Mandatory Subagent Delegation Protocol
To guarantee absolute code quality and robust division of labor, the primary agent must follow these delegation rules for any significant task:
1. **Frontend Styling & Visuals**: Segment layout/styling code blocks and invoke `frontend_designer` to build them.
2. **Frontend Interface Contracts**: Segment prop/emit declarations and store/resolver setups and invoke `frontend_architect` to review them.
3. **Mathematical & Business Logic**: Segment Polars operations or Decimal math functions and invoke `financial_expert` to implement them.
4. **Unit / Integration Testing**: Segment pytest or factory mock generation and invoke `tester` to build the test cases.
5. **Architectural Evaluation & QA**: Before finalizing modifications, invoke `architect_critic` to review the full layout, imports, and security boundaries.

---

## 3. Active Skills Registry

Skills are modular, on-demand instructions loaded only when required. They are stored in `.agents/skills/`.
- **`backend-api`**: FastAPI router and endpoint design conventions.
- **`database-models`**: SQLModel structures, schema validation, and bulk mutations.
- **`development-workflow`**: Line budget checks, directory structures, and self-corrections.
- **`financial-math`**: Decimal precision constraints and Polars performance trap mitigations.
- **`frontend-vue`**: Vue 3 composition, decoupled representation, and Tailwind v4 theme utility rules.
- **`generate-themed-component`**: Automated Vue component styling and interface contracts.
- **`git-commit`**: Mandatory commit guidelines, aliases, Conventional Commits format, and permissions.
- **`testing`**: Pytest standards, E2E Playwright verification, and factory mock conventions.

- Automatically locate, read, and load relevant skills whenever a task maps to an existing skill framework.
- Prioritize using these native skills over writing raw custom workflows from scratch.

---

### Mandatory Pre-Flight / Pre-Commit Self-Check:
Before writing code or asking for commit approval, you MUST explicitly answer and document:
1. **Size Budget**: Do any new or modified files (including test files and composables) exceed 400 lines? If yes, split them now.
2. **Reusability**: Did you reuse existing sub-components or utilities instead of copy-pasting or building monolithic files?
3. **Structure**: Are your components placed in logical subfolders instead of a flat folder? If a feature has >3 components, did you place them in a dedicated subdirectory?
4. **Decoupled API**: Is all logic decoupled (frontend is representation/interaction only, business/financial logic is in the backend)?
5. **Database Efficiency**: Did you avoid loop-based database commits and N+1 queries for batch operations?
6. **Subagent Delegation**: Did you delegate task segments to the appropriate subagents (e.g. `tester` for tests, `frontend_designer` for layout/styles, `architect_critic` for final code reviews)?
7. **Commit & Push Compliance**: Did you verify that you only commit after explicit user approval, using the `git agent-commit` alias and Conventional Commits format, and that no `git push` is executed?

