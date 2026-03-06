"""system settings table

Revision ID: 0003_system_settings
Revises: 0002_admin_crud_extensions
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_system_settings"
down_revision = "0002_admin_crud_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("admin_users.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
