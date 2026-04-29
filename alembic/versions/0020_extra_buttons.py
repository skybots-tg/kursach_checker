"""Add ContentMenuItem.extra_buttons (per-item inline button switches).

Идея: убрать «магические» текстовые маркеры вроде ``{subscribe_btn}``
и хранить дополнительные inline-кнопки пункта как явный список кодов.
Админ управляет ими через свитчи в форме редактирования пункта меню.

Revision ID: 0020_extra_buttons
Revises: 0019_pay_btn_subs_btn
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_extra_buttons"
down_revision = "0019_pay_btn_subs_btn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_menu_items",
        sa.Column(
            "extra_buttons",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    bind = op.get_bind()

    # Если в каких-то сообщениях уже использовался устаревший маркер
    # {subscribe_btn} — переносим намерение «добавь кнопку проверки
    # подписки» в новое поле extra_buttons у соответствующих пунктов
    # меню и чистим текст от маркера. Кэш copy_message инвалидируем.
    bind.execute(
        sa.text(
            """
            UPDATE content_menu_items
            SET extra_buttons = (
                SELECT to_jsonb(ARRAY(
                    SELECT DISTINCT v
                    FROM unnest(
                        COALESCE(
                            (
                                SELECT array_agg(value::text)
                                FROM json_array_elements_text(extra_buttons)
                            ),
                            ARRAY[]::text[]
                        )
                        || ARRAY['subscribe_check']
                    ) AS v
                ))
            )
            WHERE id IN (
                SELECT DISTINCT menu_item_id
                FROM menu_item_messages
                WHERE text LIKE '%{subscribe_btn}%'
            )
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE menu_item_messages
            SET text = REPLACE(text, '{subscribe_btn}', ''),
                cached_chat_id = NULL,
                cached_message_id = NULL,
                updated_at = NOW()
            WHERE text LIKE '%{subscribe_btn}%'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("content_menu_items", "extra_buttons")
