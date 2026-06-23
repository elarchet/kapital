# Alembic Database Migrations Reference

This reference documents commands and procedures for database schema migrations.

## 1. Creating Migrations
To generate an autodetected migration revision, run:
```bash
uv run alembic revision --autogenerate -m "description_of_change"
```
*Always verify the generated migration file in `backend/migrations/versions/` to ensure it matches the expected schema changes.*

## 2. Upgrading / Downgrading
* **Development**: Run `uv run alembic upgrade head` to apply migrations locally.
* **Production**: Do not run manual migrations in production without environment-gated verification.
* **Infrastructure Rule**: Never execute `alembic upgrade head` in automated test/CI runs unless explicitly approved.
