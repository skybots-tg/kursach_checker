"""Seed menu item «получи +N за подписку на канал».

Идемпотентно создаёт корневой пункт меню с ``payload = 'flow_subscribe_bonus'``
и записывает к нему дефолтное сообщение. На лету бот подменяет дочернюю
клавиатуру на пару кнопок «Перейти в канал» (URL) и «Я подписался —
проверить» (callback) — см. ``app/integrations/telegram_bot.py``.

Кэш copy_message по этому пункту мы не создаём (для текстовых сообщений
он и так не используется, см. ``telegram_messages._try_cached_send``),
поэтому отдельной инвалидации не требуется.

Также сбрасываем устаревший override для ``check.no_credits`` — там
дефолт мы поменяли (добавили блок про бонусы и переменную
``{subscribe_bonus}``), и старая запись из админки перебивала бы новый
текст.

Revision ID: 0017_subscribe_bonus
Revises: 0016_referral_text_bonus_one
Create Date: 2026-04-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_subscribe_bonus"
down_revision = "0016_referral_text_bonus_one"
branch_labels = None
depends_on = None


SUBSCRIBE_PAYLOAD = "flow_subscribe_bonus"
SUBSCRIBE_TITLE = "Получи бонус за подписку"
SUBSCRIBE_ICON = "🎁"
SUBSCRIBE_ROW = 5
SUBSCRIBE_COL = 0


SUBSCRIBE_DEFAULT_TEXT = (
    "<b>забери ещё бесплатные проверки 🎁</b>\n"
    "\n"
    "<blockquote>👉🏼 подпишись на наш канал\n"
    "👉🏼 нажми кнопку «Я подписался — проверить»\n"
    "👉🏼 мы автоматически зачислим тебе бонусные попытки</blockquote>\n"
    "\n"
    "<b>бонус выдаётся один раз — пользуйся 🚀</b>"
)


def upgrade() -> None:
    bind = op.get_bind()

    existing_id = bind.execute(
        sa.text(
            "SELECT id FROM content_menu_items WHERE payload = :p LIMIT 1"
        ),
        {"p": SUBSCRIBE_PAYLOAD},
    ).scalar()

    if existing_id is None:
        result = bind.execute(
            sa.text(
                """
                INSERT INTO content_menu_items
                    (parent_id, title, icon, item_type, payload,
                     position, "row", col, active, created_at, updated_at)
                VALUES
                    (NULL, :title, :icon, 'text', :payload,
                     :pos, :row, :col, TRUE, NOW(), NOW())
                RETURNING id
                """
            ),
            {
                "title": SUBSCRIBE_TITLE,
                "icon": SUBSCRIBE_ICON,
                "payload": SUBSCRIBE_PAYLOAD,
                "pos": SUBSCRIBE_ROW * 100 + SUBSCRIBE_COL,
                "row": SUBSCRIBE_ROW,
                "col": SUBSCRIBE_COL,
            },
        )
        item_id = result.scalar_one()
    else:
        item_id = existing_id
        bind.execute(
            sa.text(
                """
                UPDATE content_menu_items
                SET title = :title,
                    icon = :icon,
                    item_type = 'text',
                    "row" = :row,
                    col = :col,
                    position = :pos,
                    active = TRUE,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": item_id,
                "title": SUBSCRIBE_TITLE,
                "icon": SUBSCRIBE_ICON,
                "pos": SUBSCRIBE_ROW * 100 + SUBSCRIBE_COL,
                "row": SUBSCRIBE_ROW,
                "col": SUBSCRIBE_COL,
            },
        )

    has_message = bind.execute(
        sa.text(
            "SELECT id FROM menu_item_messages WHERE menu_item_id = :id LIMIT 1"
        ),
        {"id": item_id},
    ).scalar()

    if has_message is None:
        bind.execute(
            sa.text(
                """
                INSERT INTO menu_item_messages
                    (menu_item_id, position, message_type, text, parse_mode,
                     file_path, file_name, mime_type,
                     cached_chat_id, cached_message_id,
                     created_at, updated_at)
                VALUES
                    (:id, 0, 'text', :text, 'HTML',
                     NULL, NULL, NULL,
                     NULL, NULL,
                     NOW(), NOW())
                """
            ),
            {"id": item_id, "text": SUBSCRIBE_DEFAULT_TEXT},
        )

    # Старый override для check.no_credits мог не содержать переменной
    # {subscribe_bonus} — он перебьёт новый дефолт и format_map просто
    # вернёт шаблон без подстановки. Чистим именно override (значение в
    # bot_content), а не сам дефолт из кода.
    bind.execute(
        sa.text("DELETE FROM bot_content WHERE key = 'check.no_credits'")
    )


def downgrade() -> None:
    bind = op.get_bind()
    item_id = bind.execute(
        sa.text(
            "SELECT id FROM content_menu_items WHERE payload = :p LIMIT 1"
        ),
        {"p": SUBSCRIBE_PAYLOAD},
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
