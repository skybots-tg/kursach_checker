"""Add scheduled broadcasts, inline buttons, and broadcast files.

Revision ID: 0020_bc_sched_btns_files
Revises: 0019_pay_btn_subs_btn
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_bc_sched_btns_files"
down_revision = "0019_pay_btn_subs_btn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("broadcasts", sa.Column("scheduled_at", sa.DateTime(), nullable=True))
    op.add_column("broadcasts", sa.Column("admin_timezone", sa.String(64), nullable=True))

    op.add_column("broadcast_messages", sa.Column("buttons_json", sa.JSON(), nullable=True))

    op.create_table(
        "broadcast_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer(), sa.ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("media_type", sa.String(32), nullable=False, server_default="document"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("broadcast_files")
    op.drop_column("broadcast_messages", "buttons_json")
    op.drop_column("broadcasts", "admin_timezone")
    op.drop_column("broadcasts", "scheduled_at")
