"""Reset overrides for no_credits buttons and subscribe.not_subscribed.

В миграции 0017 мы уже создали текст бонуса за подписку и сбросили
устаревший override для ``check.no_credits``. Теперь подгоняем тексты
под доработанный UX:

* На экране ``check.no_credits`` появляется ещё одна кнопка
  «🏠 Вернуться в меню» (``check.no_credits_btn_home``) и
  переименована «👥 Реферальная программа»
  (``check.no_credits_btn_referral``).
* Кнопка проверки подписки теперь называется «✅ Проверить подписку»
  (``subscribe.btn_check``).
* Сообщение «не вижу твою подписку» (``subscribe.not_subscribed``)
  переписано в дружелюбной стилистике и добавлена переменная
  ``{bonus}``.

Удаляем устаревшие override'ы из ``bot_content``, чтобы новые дефолты
из ``app/services/bot_texts.py`` подхватились автоматически. Если админ
захочет — снова сможет переопределить тексты через админку.

Кеш ``copy_message`` для ``MenuItemMessage`` инвалидируем у тех пунктов,
которые могут содержать новые плейсхолдеры ({credits}, {N}, {ref_link}),
чтобы кешированная не персонализированная копия не разошлась всем.

Revision ID: 0018_no_credits_buttons_subscribe_text
Revises: 0017_subscribe_bonus
Create Date: 2026-04-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_no_credits_buttons_subscribe_text"
down_revision = "0017_subscribe_bonus"
branch_labels = None
depends_on = None


STALE_KEYS = [
    "check.no_credits_btn_referral",
    "check.no_credits_btn_subscribe",
    "subscribe.btn_check",
    "subscribe.not_subscribed",
]


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text("DELETE FROM bot_content WHERE key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True),
        ),
        {"keys": STALE_KEYS},
    )

    # На всякий случай — инвалидируем кеш у сообщений всех пунктов меню,
    # которые могут содержать новые плейсхолдеры. Кеш copy_message не даёт
    # подставлять персональные значения, поэтому без сброса риск показать
    # одинаковый текст всем пользователям.
    bind.execute(
        sa.text(
            """
            UPDATE menu_item_messages
            SET cached_chat_id = NULL,
                cached_message_id = NULL,
                updated_at = NOW()
            WHERE text IS NOT NULL
              AND (
                text LIKE '%{credits}%'
                OR text LIKE '%{N}%'
                OR text LIKE '%{ref_link}%'
              )
            """
        )
    )


def downgrade() -> None:
    # Откатывать удаление overrides не имеет смысла: миграция вверх
    # просто снова приведёт состояние к актуальному.
    pass
