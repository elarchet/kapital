"""add_ui_component_marketplace

Revision ID: e4181cc04a9d
Revises: 776a056369b8
Create Date: 2026-06-15 10:25:05.363578

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4181cc04a9d"
down_revision: str | Sequence[str] | None = "776a056369b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add column theme to user table
    op.add_column("user", sa.Column("theme", sa.String(length=50), nullable=False, server_default="slate-light"))

    # Create table ui_component_variant
    op.create_table(
        "ui_component_variant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("component_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("asset_url", sa.String(length=500), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ui_component_variant_component_key"),
        "ui_component_variant",
        ["component_key"],
        unique=False,
    )
    op.create_index(op.f("ix_ui_component_variant_is_active"), "ui_component_variant", ["is_active"], unique=False)
    op.create_index(op.f("ix_ui_component_variant_user_id"), "ui_component_variant", ["user_id"], unique=False)

    # Create table ui_component_override
    op.create_table(
        "ui_component_override",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("component_key", sa.String(length=100), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["ui_component_variant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ui_component_override_component_key"),
        "ix_ui_component_override",
        ["component_key"],
        unique=False,
    )
    op.create_index(op.f("ix_ui_component_override_is_active"), "ix_ui_component_override", ["is_active"], unique=False)
    op.create_index(op.f("ix_ui_component_override_user_id"), "ix_ui_component_override", ["user_id"], unique=False)
    op.create_index(op.f("ix_ui_component_override_variant_id"), "ui_component_override", ["variant_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_ui_component_override_variant_id"), table_name="ui_component_override")
    op.drop_index(op.f("ix_ui_component_override_user_id"), table_name="ui_component_override")
    op.drop_index(op.f("ix_ui_component_override_is_active"), table_name="ui_component_override")
    op.drop_index(op.f("ix_ui_component_override_component_key"), table_name="ui_component_override")
    op.drop_table("ui_component_override")

    op.drop_index(op.f("ix_ui_component_variant_user_id"), table_name="ui_component_variant")
    op.drop_index(op.f("ix_ui_component_variant_is_active"), table_name="ui_component_variant")
    op.drop_index(op.f("ix_ui_component_variant_component_key"), table_name="ui_component_variant")
    op.drop_table("ui_component_variant")

    op.drop_column("user", "theme")
