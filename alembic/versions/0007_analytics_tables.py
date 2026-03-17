"""Add analytics tables: user_events, user_sessions, user_statuses, daily_analytics

Revision ID: 0007_analytics_tables
Revises: 0006_telegram_id_bigint
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0007_analytics_tables"
down_revision = "0006_telegram_id_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_category", sa.String(64), nullable=False, server_default="action"),
        sa.Column("event_data", JSONB(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])
    op.create_index("ix_user_events_telegram_id", "user_events", ["telegram_id"])
    op.create_index("ix_user_events_event_type", "user_events", ["event_type"])
    op.create_index("ix_user_events_session_id", "user_events", ["session_id"])
    op.create_index("ix_user_events_created_at", "user_events", ["created_at"])
    op.create_index("ix_user_events_user_created", "user_events", ["user_id", "created_at"])
    op.create_index("ix_user_events_type_created", "user_events", ["event_type", "created_at"])
    op.create_index("ix_user_events_category_created", "user_events", ["event_category", "created_at"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("session_id", sa.String(64), unique=True, nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("events_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("platform", sa.String(64), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_session_id", "user_sessions", ["session_id"])

    op.create_table(
        "user_statuses",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(), nullable=True),
        sa.Column("unblocked_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("total_events", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_sessions", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_user_statuses_is_blocked", "user_statuses", ["is_blocked"])
    op.create_index("ix_user_statuses_is_deleted", "user_statuses", ["is_deleted"])

    op.create_table(
        "daily_analytics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("metric_name", sa.String(64), nullable=False),
        sa.Column("metric_value", sa.Integer(), server_default="0", nullable=False),
        sa.Column("breakdown", JSONB(), nullable=True),
    )
    op.create_index("ix_daily_analytics_date", "daily_analytics", ["date"])
    op.create_index("ix_daily_analytics_metric_name", "daily_analytics", ["metric_name"])
    op.create_index(
        "ix_daily_analytics_date_metric",
        "daily_analytics",
        ["date", "metric_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("daily_analytics")
    op.drop_table("user_statuses")
    op.drop_table("user_sessions")
    op.drop_table("user_events")
