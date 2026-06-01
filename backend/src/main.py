from __future__ import annotations

from collections.abc import AsyncGenerator  # noqa: TC003
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db
from src.routers import (
    auth,
    financial_account,
    financial_info,
    import_file_schema,
    institution,
    operation,
    portfolio,
    position,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Handles startup actions (like auto table creation) and teardown context."""
    init_db()
    yield


app = FastAPI(
    title="Kapital API",
    description="Wealth management and financial analytics REST API backend.",
    version="0.1.0",
    lifespan=lifespan,
)

# Robust CORS middleware ready for detached Vue.js frontend (Phase 2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under the unified /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(position.router, prefix="/api")
app.include_router(institution.router, prefix="/api")
app.include_router(financial_account.router, prefix="/api")
app.include_router(operation.router, prefix="/api")
app.include_router(import_file_schema.router, prefix="/api")
app.include_router(financial_info.router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    """Health check/welcome endpoint."""
    return {"message": "Welcome to Kapital API. Access API docs at /docs"}
