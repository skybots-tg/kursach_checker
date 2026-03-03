"""admin crud extensions

Revision ID: 0002_admin_crud_extensions
Revises: 0001_initial
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_admin_crud_extensions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_menu_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("content_menu_items.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_content_menu_items_parent_id", "content_menu_items", ["parent_id"], unique=False)

    op.create_table(
        "content_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
    )
    op.create_index("ix_content_versions_key", "content_versions", ["key"], unique=False)

    op.create_table(
        "check_worker_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("checks.id"), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_check_worker_logs_check_id", "check_worker_logs", ["check_id"], unique=False)

    op.create_table(
        "demo_samples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("document_file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=True),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_demo_samples_name", "demo_samples", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_demo_samples_name", table_name="demo_samples")
    op.drop_table("demo_samples")

    op.drop_index("ix_check_worker_logs_check_id", table_name="check_worker_logs")
    op.drop_table("check_worker_logs")

    op.drop_index("ix_content_versions_key", table_name="content_versions")
    op.drop_table("content_versions")

    op.drop_index("ix_content_menu_items_parent_id", table_name="content_menu_items")
    op.drop_table("content_menu_items")
