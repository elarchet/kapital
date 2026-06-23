---
name: development-workflow
description: Code quality checks, size budgets, Git conventions, and self-checks.
---

# Development & Git Workflow Standards

This skill details behavioral protocols for commits, code structures, and size constraints.

## 1. File Size Discipline & Structure
- **Size Budget**: No file (Vue component, Python module, helper composable, test file, etc.) should exceed ~400 lines. If a file approaches this limit, refactor it immediately:
  - For frontend components, extract sub-composables (e.g., separating executor, processor, and state wizard concerns) or sub-components.
  - For test files, split the test suite into logical sub-test files (e.g., `test_import.py` and `test_import_custom.py`).
- **Symmetric Layout**: Python backend in `backend/src/` (tests in `backend/tests/`); frontend in `frontend/src/`.
- **Subfolders Over Flat Dirs**: Group related components into subfolders (e.g., `components/import/`). Never keep flat directories with many files.

## 2. Git & Verification Flow
- **Execution Protocol**: Always use the custom alias `git agent-commit` for all commits (applies the `Antigravity Agent` identity).
- **Atomic Commits**: One logical change = One commit. Stage only specific hunks or files for a single logical change (use `git add -p`).
- **Commit Format**: Format messages yourself as strict Conventional Commits (e.g., `git agent-commit -m "type(scope): message"`) to pass `commitizen check`.
- **Permissions**:
  - **Committing**: Do not commit without presenting the changes and receiving explicit user approval.
  - **Pushing**: `git push` in any form is strictly forbidden.
- **Self-Correction**: If a test fails, analyze the logs and fix it before asking for help. Do not commit broken states.
