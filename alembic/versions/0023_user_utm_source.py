"""Add utm_source column to users table.

Revision ID: 0023_user_utm_source
Revises: 0022_merge_heads
Create Date: 2026-05-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0023_user_utm_source"
down_revision = "0022_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("utm_source", sa.String(128), nullable=True))
    op.create_index("ix_users_utm_source", "users", ["utm_source"])


def downgrade() -> None:
    op.drop_index("ix_users_utm_source", table_name="users")
    op.drop_column("users", "utm_source")
