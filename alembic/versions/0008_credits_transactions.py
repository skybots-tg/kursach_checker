"""Add credits_transactions table for balance history

Revision ID: 0008_credits_transactions
Revises: 0007_analytics_tables
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_credits_transactions"
down_revision = "0007_analytics_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credits_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("tx_type", sa.String(32), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("reference_type", sa.String(64), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("credits_transactions")
