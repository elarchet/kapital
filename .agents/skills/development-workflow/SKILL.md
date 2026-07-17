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
- **Git Commit Workflow**: Refer to and strictly follow the [git-commit](../git-commit/SKILL.md) skill for commit aliases, formatting conventions, permissions, and approval processes.
- **Self-Correction**: If a test fails, analyze the logs and fix it before asking for help. Do not request commit approval for broken states.
