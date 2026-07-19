"""asset_price table

Persist daily market closes per ticker symbol (global, shared across users)
so portfolio valuation can chart market value over time without re-fetching
full histories from yfinance on every request.

Guarded with inspector checks because 0001 builds the whole current metadata
via ``create_all`` — on a fresh database this table already exists.

Revision ID: 0004_asset_price
Revises: 0003_loaded_not_imported
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_asset_price"
down_revision = "0003_loaded_not_imported"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the asset_price table with its uniqueness and lookup indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("asset_price"):
        op.create_table(
            "asset_price",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("price_date", sa.Date(), nullable=False),
            sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("symbol", "price_date", name="uq_asset_price_symbol_date"),
        )
        op.create_index(op.f("ix_asset_price_symbol"), "asset_price", ["symbol"])
        op.create_index(op.f("ix_asset_price_price_date"), "asset_price", ["price_date"])


def downgrade() -> None:
    """Drop the asset_price table."""
    op.drop_index(op.f("ix_asset_price_price_date"), table_name="asset_price")
    op.drop_index(op.f("ix_asset_price_symbol"), table_name="asset_price")
    op.drop_table("asset_price")
