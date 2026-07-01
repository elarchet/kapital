FROM python:3.14-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy project specification files
COPY pyproject.toml uv.lock ./

# Sync dependencies without dev groups or installing the root package itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Final runtime stage
FROM python:3.14-slim

WORKDIR /app

# Copy the synced virtualenv
COPY --from=builder /app/.venv /app/.venv

# Ensure virtualenv binaries are in path
ENV PATH="/app/.venv/bin:$PATH"

# Copy backend application files
COPY src /app/src
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

EXPOSE 8000

# Run FastAPI backend
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
