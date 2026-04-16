"""Reserve a ContentMenuItem for /start media messages.

Идемпотентно заводит «служебный» пункт меню с ``payload = '__start__'``.
Он не отображается в главной клавиатуре, но админ может прикрепить к нему
любые сообщения (текст, фото, видео, кружок, GIF, аудио, документ) во вкладке
«Тексты» — эти сообщения бот отправит ДО приветствия ``bot.welcome`` при
команде /start.

Revision ID: 0013_start_media_item
Revises: 0012_content_rebrand
Create Date: 2026-04-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_start_media_item"
down_revision = "0012_content_rebrand"
branch_labels = None
depends_on = None


START_PAYLOAD = "__start__"


def upgrade() -> None:
    bind = op.get_bind()

    existing = bind.execute(
        sa.text("SELECT id FROM content_menu_items WHERE payload = :p LIMIT 1"),
        {"p": START_PAYLOAD},
    ).scalar()
    if existing is not None:
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO content_menu_items
                (parent_id, title, icon, item_type, payload,
                 position, "row", col, active, created_at, updated_at)
            VALUES
                (NULL, :title, :icon, 'text', :payload,
                 :pos, :row, :col, TRUE, NOW(), NOW())
            """
        ),
        {
            "title": "Стартовое сообщение /start",
            "icon": "🏠",
            "payload": START_PAYLOAD,
            # -100000, чтобы гарантированно не пересекаться с реальными
            # пунктами меню (у них row >= 0).
            "pos": -100000,
            "row": -1000,
            "col": 0,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    item_id = bind.execute(
        sa.text("SELECT id FROM content_menu_items WHERE payload = :p LIMIT 1"),
        {"p": START_PAYLOAD},
    ).scalar()
    if item_id is None:
        return
    bind.execute(
        sa.text("DELETE FROM menu_item_messages WHERE menu_item_id = :id"),
        {"id": item_id},
    )
    bind.execute(
        sa.text("DELETE FROM content_menu_items WHERE id = :id"),
        {"id": item_id},
    )
