# Antigravity Behavioral Rules

## Coding Philosophy
- **Official-Only**: Use official library documentation. Avoid unverified Stack Overflow snippets.
- **Defensive Programming**: Always handle potential `None` types from financial APIs. Use `try-except` blocks for all external institution connections.
- **Type Safety**: No `Any` allowed. If a type is unknown, use `Protocol` or `Union`.
- **Conciseness**: Avoid excessive or obvious code comments. Restrict comments to only highly useful, non-obvious explanations (the "why", not the "what").

## Git & Automation
- **Execution Protocol**:
  - You **MUST** use the custom alias `git agent-commit` for all commits.
  - This alias automatically applies the identity `Antigravity Agent`.
  - **Arg Passing**: If you need to pass extra Git flags (e.g., `--allow-empty`), append them normally: `git agent-commit --allow-empty`.

- **Atomic Commits**:
  - **Constraint**: One logical change = One commit. Do not bundle unrelated refactors, fixes, or features.
  - **Workflow**: 
    1. Stage only the specific hunks or files for a single logical change (use `git add -p` logic).
    2. Verify the **"Green"** state (Lint + Tests) for *that specific change only*.
    3. Once verified, ask the user for explicit approval to commit. Do not execute the commit until permission is granted.

- **Commit Format**: As an agent, you must format the message as a **strict Conventional Commit** yourself to ensure it passes the `commitizen check` pre-commit hook defined in `prek.toml`. Use the non-interactive alias `git agent-commit -m "type(scope): message"`. Do not use `cz` interactively.

- **Self-Correction**: If a test fails, analyze the logs and fix the code before asking the user for help. Do not commit "Broken" states.

## Permissions
- **Committing**: Do not execute `git commit` (or `git agent-commit`) without asking for and receiving explicit approval from the user first. Always present the changes you intend to commit.
- **Pushing**: `git push` (in any form, including `--force` or `--force-with-lease`) is strictly forbidden. Only the user may push to the remote.
- **Infrastructure**: You may generate Alembic migrations, but never run `alembic upgrade head` without a manual "Go" from the user.
- **Deletions**: Strictly forbidden without explicit confirmation.

## Repository Structure
- **Symmetric Layout**: All Python backend source code lives in `backend/src/` and tests live in `backend/tests/`. All frontend code lives in `frontend/`.
- **Command Execution**: Always execute Python/backend commands (like prek, pytest, uvicorn) using the `--directory backend` flag or by navigating into the `backend/` directory first. Always use `uv` as the python manager for running commands (e.g., prefix with `uv run`).

## Frontend Guidelines
- **Clean Decoupling**: Keep frontend code fully decoupled from the backend REST API. Ensure API endpoints are structured, documented, and fully type-safe.
- **Component Privilege**: When adding a feature, privilege components over views when possible (reusability is key).
- **Frontend Testing**: If frontend testing is available, run it at the very end of development to ensure no issues were introduced. If no frontend tests are available, at least try to run the application to verify that it starts and loads correctly.

## Parametrization & Configurability
- **Maximize Parameters**: For both frontend and backend, use as many parameters/options as possible to let the user easily and quickly tweak the app.

## Testing & Quality Workflow
- **No Initial Tests**: Do not run `pytest` at the beginning of your analysis. Consider all tests valid when you have not added or modified any code.
- **Feature Tests**: When adding a feature, add as many tests as required.
- **Selective Run**: When a feature is ready, if possible run only the tests related to the modifications. In case of doubt, run all tests.
- **Prek Timing**: Run `prek` only at the very end when you want to commit, not before.

## Documentation
- Document REST API endpoints and complex service logic to facilitate seamless frontend integration.