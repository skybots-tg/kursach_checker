"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("credits_amount", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "universities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "gosts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
    )
    op.create_index("ix_admin_users_login", "admin_users", ["login"], unique=True)

    op.create_table(
        "credits_balance",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("credits_available", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("university_id", sa.Integer(), sa.ForeignKey("universities.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type_work", sa.String(length=100), nullable=False),
        sa.Column("year", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_templates_university_id", "templates", ["university_id"], unique=False)

    op.create_table(
        "template_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("templates.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
    )
    op.create_index("ix_template_versions_template_id", "template_versions", ["template_id"], unique=False)

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)

    op.create_table(
        "payments_prodamus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("prodamus_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_payments_prodamus_order_id", "payments_prodamus", ["order_id"], unique=False)

    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("template_version_id", sa.Integer(), sa.ForeignKey("template_versions.id"), nullable=False),
        sa.Column("gost_id", sa.Integer(), sa.ForeignKey("gosts.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=False),
        sa.Column("result_report_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=True),
        sa.Column("output_file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_checks_user_id", "checks", ["user_id"], unique=False)

    op.create_table(
        "bot_content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_bot_content_key", "bot_content", ["key"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("diff_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index("ix_bot_content_key", table_name="bot_content")
    op.drop_table("bot_content")
    op.drop_index("ix_checks_user_id", table_name="checks")
    op.drop_table("checks")
    op.drop_index("ix_payments_prodamus_order_id", table_name="payments_prodamus")
    op.drop_table("payments_prodamus")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("files")
    op.drop_index("ix_template_versions_template_id", table_name="template_versions")
    op.drop_table("template_versions")
    op.drop_index("ix_templates_university_id", table_name="templates")
    op.drop_table("templates")
    op.drop_table("credits_balance")
    op.drop_index("ix_admin_users_login", table_name="admin_users")
    op.drop_table("admin_users")
    op.drop_table("gosts")
    op.drop_table("universities")
    op.drop_table("products")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

