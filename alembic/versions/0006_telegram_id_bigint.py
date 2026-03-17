"""Widen users.telegram_id to BigInteger

Revision ID: 0006_telegram_id_bigint
Revises: 0005_gost_university_link
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_telegram_id_bigint"
down_revision = "0005_gost_university_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
