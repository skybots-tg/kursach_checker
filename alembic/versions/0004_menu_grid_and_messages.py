"""Add row/col to content_menu_items, create menu_item_messages table

Revision ID: 0004_menu_grid_and_messages
Revises: 0003_system_settings
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_menu_grid_and_messages"
down_revision = "0003_system_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_menu_items",
        sa.Column("row", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "content_menu_items",
        sa.Column("col", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "menu_item_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "menu_item_id",
            sa.Integer(),
            sa.ForeignKey("content_menu_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message_type", sa.String(32), nullable=False, server_default="text"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("parse_mode", sa.String(16), nullable=False, server_default="HTML"),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("cached_chat_id", sa.Integer(), nullable=True),
        sa.Column("cached_message_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("menu_item_messages")
    op.drop_column("content_menu_items", "col")
    op.drop_column("content_menu_items", "row")
