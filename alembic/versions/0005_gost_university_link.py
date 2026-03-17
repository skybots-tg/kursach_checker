"""Add university_id to gosts table

Revision ID: 0005_gost_university_link
Revises: 0004_menu_grid_and_messages
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_gost_university_link"
down_revision = "0004_menu_grid_and_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gosts", sa.Column("university_id", sa.Integer(), nullable=True))
    op.create_index("ix_gosts_university_id", "gosts", ["university_id"])
    op.create_foreign_key(
        "fk_gosts_university_id",
        "gosts",
        "universities",
        ["university_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_gosts_university_id", "gosts", type_="foreignkey")
    op.drop_index("ix_gosts_university_id", table_name="gosts")
    op.drop_column("gosts", "university_id")
