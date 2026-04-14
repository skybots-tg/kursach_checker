"""Add target_segment column to broadcasts

Revision ID: 0011_broadcast_segments
Revises: 0010_broadcasts
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_broadcast_segments"
down_revision = "0010_broadcasts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broadcasts",
        sa.Column(
            "target_segment",
            sa.JSON(),
            nullable=False,
            server_default='{"type":"all"}',
        ),
    )


def downgrade() -> None:
    op.drop_column("broadcasts", "target_segment")
