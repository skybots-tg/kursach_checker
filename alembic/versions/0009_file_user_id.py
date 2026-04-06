"""Add user_id column to files table

Revision ID: 0009_file_user_id
Revises: 0008_credits_transactions
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_file_user_id"
down_revision = "0008_credits_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("files", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_files_user_id", "files", "users", ["user_id"], ["id"])
    op.create_index("ix_files_user_id", "files", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_files_user_id", table_name="files")
    op.drop_constraint("fk_files_user_id", "files", type_="foreignkey")
    op.drop_column("files", "user_id")
