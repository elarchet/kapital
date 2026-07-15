"""initial schema — raw transaction + allocation model

Fresh baseline for the transaction-split refactor. Builds the entire schema
directly from the SQLModel metadata so the DDL always matches the ORM models.
Alpha stage: no legacy migration chain is preserved.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-09
"""

from __future__ import annotations

from sqlmodel import SQLModel

import src.models  # noqa: F401  (register all tables on the metadata)
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create every table defined by the current SQLModel metadata."""
    SQLModel.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Drop every table defined by the current SQLModel metadata."""
    SQLModel.metadata.drop_all(bind=op.get_bind())
