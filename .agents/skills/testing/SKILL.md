---
name: testing
description: Testing workflow using pytest, pytest-asyncio, factory_boy mock generation, and test execution standards.
---

# Testing & Quality Assurance Standards

This skill details how to write and execute unit and integration tests.

## 1. Pytest & Async Testing
- Use `pytest` and `pytest-asyncio` for all backend code.
- Focus on testing logic and service layers independently of the DB where possible, or use SQLite in-memory for DB tests.
- Target 100% test coverage for all financial calculation modules (`backend/src/services/` or `backend/src/logic/`).
- **Test Suite Splitting**: Strictly respect the ~400-line budget limit for all test files (e.g., `test_*.py`). Split large test files into focused feature tests (e.g., `test_import_custom.py`) to keep files highly readable, maintainable, and within line budget limits.

## 2. Test Data Generation
- Use `factory_boy` and `factory.Faker` to generate mock data dynamically.
- Avoid manual, hardcoded dummy instantiations in tests to ensure diverse inputs and test robustness, unless specific edge-case numbers are required.

## 3. Local Verification Protocol
- During active feature development, run tests locally for the specific module under test:
  ```bash
  uv run pytest backend/tests/test_specific.py
  ```
- Do not run the full verification suite (`prek` or global pytest run) automatically on startup or before the user reviews/approves changes.

## 4. Frontend E2E / QA Testing (Playwright)
- Use Playwright for all frontend E2E and visual QA verification.
- Write E2E test files in `frontend/e2e/` with `.spec.ts` extensions.
- Execute Playwright E2E tests from the `frontend/` directory with:
  ```bash
  PATH="/home/etien/dev/perso/kapital/.node-dist/bin:$PATH" npx playwright test
  ```
- The dev server (`npm run dev`) is automatically launched and managed by Playwright's `webServer` config block.

