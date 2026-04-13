"""Add broadcasts and broadcast_messages tables

Revision ID: 0010_broadcasts
Revises: 0009_file_user_id
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_broadcasts"
down_revision = "0009_file_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "broadcast_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("broadcast_id", sa.Integer(), sa.ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message_type", sa.String(32), nullable=False, server_default="text"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("parse_mode", sa.String(16), nullable=False, server_default="HTML"),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_broadcast_messages_broadcast_id", "broadcast_messages", ["broadcast_id"])


def downgrade() -> None:
    op.drop_index("ix_broadcast_messages_broadcast_id", table_name="broadcast_messages")
    op.drop_table("broadcast_messages")
    op.drop_table("broadcasts")
