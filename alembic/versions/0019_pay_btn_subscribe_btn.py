"""Add «Оплатить» button on no_credits screen + universal {subscribe_btn} marker.

Revision ID: 0019_pay_btn_subs_btn
Revises: 0018_btns_subs_text
Create Date: 2026-04-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_pay_btn_subs_btn"
down_revision = "0018_btns_subs_text"
branch_labels = None
depends_on = None


# Дефолт у этих ключей в коде сменился — старые override'ы из админки
# удаляем, чтобы новый текст подхватился. Если админ снова захочет
# своё значение — переопределит через UI.
STALE_KEYS = [
    # Был «👥 Реферальная программа», стал «👥 Пригласить друга».
    "check.no_credits_btn_referral",
]


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text("DELETE FROM bot_content WHERE key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True),
        ),
        {"keys": STALE_KEYS},
    )

    # Инвалидируем кэш copy_message у сообщений с маркером {subscribe_btn}.
    # Без сброса бот может прислать кешированную копию без удалённого
    # маркера и без прикреплённой кнопки.
    bind.execute(
        sa.text(
            """
            UPDATE menu_item_messages
            SET cached_chat_id = NULL,
                cached_message_id = NULL,
                updated_at = NOW()
            WHERE text IS NOT NULL
              AND text LIKE '%{subscribe_btn}%'
            """
        )
    )


def downgrade() -> None:
    pass
