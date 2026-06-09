# Antigravity Behavioral Rules

## Coding Philosophy
- **Think Before Coding**: Don't assume. State assumptions explicitly. If uncertain or multiple interpretations exist, stop and ask. Suggest simpler approaches.
- **Simplicity First**: Write the minimum code that solves the problem.
  * Do not build features or capabilities beyond what was explicitly requested.
  * Do not create abstractions, components, or helper functions for single-use code. Keep it inline until a second use case arises.
  * Do not write error handling or edge-case handling for scenarios that cannot occur in the current application context.
  * Always ask: "Would a senior engineer review this and call it overcomplicated or gold-plated?" If yes, simplify.
- **Surgical Changes**: Touch only what you must. Match existing style. Don't "improve" adjacent unrelated code, comments, or formatting. Clean up imports/variables/functions orphaned *only* by your changes.
  * *Exception*: If a file you are modifying is already oversized (>400 lines) or structurally messy, you MUST proactively refactor it (split it, extract components) as part of the current task.
- **Official-Only**: Use official library documentation. Avoid unverified Stack Overflow snippets.
- **Defensive & Type Safe**: Handle potential `None` types from financial APIs. Use `try-except` for external connection. Do not use `Any` (use `Protocol` or `Union`).
- **Conciseness**: Avoid excessive or obvious code comments. Restrict comments to highly useful, non-obvious explanations ("why", not "what").
- **Configurability**: Maximize parameters/options in both frontend and backend to let the user easily tweak the app.
- **Documentation**: Document REST API endpoints and complex service logic for seamless integration.
- **Goal-Driven Execution**: Define success criteria. State a brief step-by-step plan and loop until verified. Each step should have a clear verification check.

## Git & Verification Flow
- **Execution Protocol**: Always use the custom alias `git agent-commit` for all commits (applies the `Antigravity Agent` identity).
- **Atomic Commits**: One logical change = One commit. Stage only specific hunks or files for a single logical change (use `git add -p`).
- **Commit Format**: Format messages yourself as strict Conventional Commits (e.g., `git agent-commit -m "type(scope): message"`) to pass `commitizen check`.
- **Self-Correction**: If a test fails, analyze the logs and fix it before asking for help. Do not commit broken states.
- **Permissions**:
  * **Committing**: Do not commit without presenting the changes and receiving explicit user approval.
  * **Pushing**: `git push` in any form is strictly forbidden.
  * **Infrastructure**: Generate Alembic migrations, but never run `alembic upgrade head` without manual approval.

## Repository & Frontend Structure
- **Symmetric Layout**: Python backend in `backend/src/` (tests in `backend/tests/`); frontend in `frontend/src/`.
- **Command Execution**: Run backend commands using the `--directory backend` flag or by navigating into the `backend/` directory first, always prefixed with `uv run`.
- **Clean Decoupling**: Keep frontend decoupled from the backend. Business and financial logic belongs in the backend (`backend/src/services/` or `backend/src/logic/`).
- **Tailwind First**: Style components using Tailwind CSS v4 utilities. Empty or near-empty `<style scoped>` blocks. Declare theme variables once in `frontend/src/style.css`.
- **File Size Discipline**: Vue components and Python modules must stay under ~400 lines. Proactively split files when approaching this limit.
- **Subfolders Over Flat Dirs**: Group related components into subfolders (e.g., `components/import/`). Never keep flat directories with many files.

## Testing & Quality Workflow
- **No Initial Tests**: Do not run `pytest` at the beginning of your analysis.
- **Feature Tests**: When adding a feature, write the necessary tests but do not run global suites or hooks yet.
- **Verification Deferred (Crucial)**: Focus strictly on implementing the feature first. Do **NOT** run heavy verification processes (`prek`, `npm run build`, or full test suites) automatically. Wait until the user has reviewed the code and explicitly says it is OK.
- **Local Dev Checking Only**: During active development, you may run small, isolated test files (e.g., `uv run pytest backend/tests/test_specific.py`) to verify your logic, but avoid running full project validation suites until given the go-ahead.

### Mandatory Pre-Flight / Pre-Commit Self-Check:
Before writing code or asking for commit approval, you MUST explicitly answer and document:
1. **Size Budget**: Do any new or modified files exceed 400 lines? If yes, split them now.
2. **Reusability**: Did you reuse existing sub-components or utilities instead of copy-pasting or building monolithic files?
3. **Structure**: Are your components placed in logical subfolders instead of a flat folder? If a feature has >3 components, did you place them in a dedicated subdirectory?
4. **Decoupled API**: Is all logic decoupled (frontend is representation/interaction only, business/financial logic is in the backend)?