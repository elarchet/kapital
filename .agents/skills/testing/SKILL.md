---
name: testing
description: Testing workflow using pytest, pytest-asyncio, factory_boy mock generation, and test execution standards.
---

# Testing & Quality Assurance Standards

This skill details how to write and execute unit and integration tests.

## 1. Pytest & Async Testing
- Use `pytest` and `pytest-asyncio` for all backend code.
- Focus on testing logic and service layers independently of the DB where possible, or use a PostgreSQL test database for DB tests.
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
  npx playwright test
  ```
- The dev server (`npm run dev`) is automatically launched and managed by Playwright's `webServer` config block. When the dev docker stack is already running (backend :8000, vite :3000), the config reuses those servers instead.

### Running e2e in the dev VM (no host browsers, host npm unusable)
Host `frontend/node_modules` is a root-owned volume mountpoint, so run the suite in the official Playwright image against the live dev containers. The version tag must match the locked `@playwright/test` version:
```bash
docker run --rm --network host --ipc=host \
  -v "$PWD/frontend:/repo:ro" -v kapital-pw-work:/work \
  -w /work mcr.microsoft.com/playwright:v1.61.1-noble bash -c "
    tar -C /repo --exclude node_modules --exclude test-results \
        --exclude playwright-report -cf - . | tar -C /work -xf - &&
    [ -x node_modules/.bin/playwright ] || npm ci &&
    npx playwright test --reporter=list
  "
```
- **`--ipc=host` is mandatory.** Docker's default 64MB `/dev/shm` starves the browser's shared-memory IPC: long tests freeze mid-flow (renderer main thread blocks in futex wait, clicks never complete, the freeze point drifts run to run). Short tests can pass, which makes it look like an app bug — it isn't.
- The named volume `kapital-pw-work` caches `node_modules` between runs; the tar-copy refreshes sources into it.
- Seed login for specs: `test@example.com` / `password123` — create it with `docker exec kapital-backend-dev python -m src.seed_test_user`.
- Specs run against the *persistent* dev DB: make imported data unique per run (e.g. `Date.now()` in transaction IDs), and self-heal at the start of a spec by deleting leftovers from aborted runs through the API (grab the token from `localStorage['kapital_token']`, then `page.request` with a Bearer header).
- Backend real-file import tests (`test_import_real_files.py`) read gitignored broker exports from `data/` and auto-skip when the folder is absent.
- **Terminal-Visible Exit Codes & Reporters**: Always use a dual-reporter setup combining a terminal-friendly reporter (`list` or `line`) with the `html` reporter in `playwright.config.ts`.
  - The `html` reporter alone prints **no** error details to terminal stdout/stderr, causing test failures to be completely silent/invisible to automated CLI-based runners and agent loops.
  - Recommended config format:
    ```typescript
    reporter: [
      ['list', { printFailuresInline: true }],
      ['html', { open: 'on-failure' }]
    ]
    ```

