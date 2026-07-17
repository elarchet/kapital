"""imported_file table + raw_transaction provenance FK

Persist every uploaded import file (deduplicated per user by content hash)
and link each raw transaction to the file it came from.

Guarded with inspector checks because 0001 builds the whole current metadata
via ``create_all`` — on a fresh database these objects already exist.

Revision ID: 0002_imported_file
Revises: 0001_initial_schema
Create Date: 2026-07-16
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_imported_file"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create imported_file and add raw_transaction.imported_file_id."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("imported_file"):
        op.create_table(
            "imported_file",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("content_type", sa.String(length=100), nullable=True),
            sa.Column("storage_key", sa.String(length=255), nullable=False),
            sa.Column("last_imported_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("user_id", "sha256", name="uq_imported_file_user_sha"),
        )
        op.create_index(op.f("ix_imported_file_user_id"), "imported_file", ["user_id"])
        op.create_index(op.f("ix_imported_file_sha256"), "imported_file", ["sha256"])

    raw_txn_columns = {col["name"] for col in inspector.get_columns("raw_transaction")}
    if "imported_file_id" not in raw_txn_columns:
        op.add_column(
            "raw_transaction",
            sa.Column("imported_file_id", sa.Integer(), sa.ForeignKey("imported_file.id"), nullable=True),
        )
        op.create_index(op.f("ix_raw_transaction_imported_file_id"), "raw_transaction", ["imported_file_id"])


def downgrade() -> None:
    """Drop raw_transaction.imported_file_id and the imported_file table."""
    op.drop_index(op.f("ix_raw_transaction_imported_file_id"), table_name="raw_transaction")
    op.drop_column("raw_transaction", "imported_file_id")
    op.drop_index(op.f("ix_imported_file_sha256"), table_name="imported_file")
    op.drop_index(op.f("ix_imported_file_user_id"), table_name="imported_file")
    op.drop_table("imported_file")
