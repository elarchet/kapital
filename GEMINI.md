# Antigravity Behavioral Rules

## Coding Philosophy
- **Official-Only**: Use official library documentation. Avoid unverified Stack Overflow snippets.
- **Defensive Programming**: Always handle potential `None` types from financial APIs. Use `try-except` blocks for all external institution connections.
- **Type Safety**: No `Any` allowed. If a type is unknown, use `Protocol` or `Union`.
- **Conciseness**: Avoid excessive or obvious code comments. Restrict comments to only highly useful, non-obvious explanations (the "why", not the "what").

## Git & Automation
- **Execution Protocol**:
  - You **MUST** use the custom alias `git agent-cz` for all commits.
  - This alias automatically applies the identity `Antigravity Agent`.
  - **Arg Passing**: If you need to pass extra Git flags (e.g., `--allow-empty`), append them normally: `git agent-cz --allow-empty`.

- **Atomic Commits**:
  - **Constraint**: One logical change = One commit. Do not bundle unrelated refactors, fixes, or features.
  - **Workflow**: 
    1. Stage only the specific hunks or files for a single logical change (use `git add -p` logic).
    2. Verify the **"Green"** state (Lint + Tests) for *that specific change only*.
    3. Commit immediately using the alias before moving to the next logical unit.

- **Commit Format**: Use the interactive `git agent-cz` (Conventional Commits). If running in a non-interactive shell, use `git agent-cz -m "type(scope): message"`.

- **Self-Correction**: If a test fails, analyze the logs and fix the code before asking the user for help. Do not commit "Broken" states.

## Permissions
- **Infrastructure**: You may generate Alembic migrations, but never run `alembic upgrade head` without a manual "Go" from the user.
- **Deletions**: Strictly forbidden without explicit confirmation.

## Marimo Guidelines
- **No Logic in Notebooks**: Do not write heavy calculations inside Marimo `@app.cell` blocks. Import them from `src/`.

## Documentation
- Document every Marimo notebook as if it were a functional specification for the future Vue frontend.