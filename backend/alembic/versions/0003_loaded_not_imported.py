"""imported_file.last_imported_at becomes nullable

Files are now persisted as soon as they are loaded into the import wizard,
before (and even without) an actual transaction import. NULL means "stored
but never imported"; the timestamp is set/bumped only by real imports.

Guarded because 0001 builds the whole current metadata via ``create_all`` —
a fresh database already has the column nullable.

Revision ID: 0003_loaded_not_imported
Revises: 0002_imported_file
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_loaded_not_imported"
down_revision = "0002_imported_file"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the NOT NULL constraint on imported_file.last_imported_at."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {col["name"]: col for col in inspector.get_columns("imported_file")}
    if not columns["last_imported_at"]["nullable"]:
        op.alter_column(
            "imported_file",
            "last_imported_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )


def downgrade() -> None:
    """Restore NOT NULL (loaded-only rows fall back to their created_at)."""
    op.execute("UPDATE imported_file SET last_imported_at = created_at WHERE last_imported_at IS NULL")
    op.alter_column(
        "imported_file",
        "last_imported_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
