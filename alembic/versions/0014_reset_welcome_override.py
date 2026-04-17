"""Drop stale bot_content overrides that block the new customer-approved defaults.

В таблице ``bot_content`` лежат переопределения системных текстов, которые
админка пишет поверх дефолтов из ``app/services/bot_texts.py``. Если там
осталось старое значение (например, заглушка «Привет! 👋 Я помогу…»), оно
перебивает новый дефолт из кода и новые тексты на /start не видны.

Эта миграция идемпотентно удаляет именно те записи, дефолты которых мы
поменяли в ходе рестайлинга от заказчика 16.04.2026. Если админ захочет —
сможет снова переопределить их через админку.

Revision ID: 0014_reset_welcome_override
Revises: 0013_start_media_item
Create Date: 2026-04-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_reset_welcome_override"
down_revision = "0013_start_media_item"
branch_labels = None
depends_on = None


# Ключи, дефолты которых мы меняли в миграциях 0012+. Переопределения с
# устаревшим содержимым мы чистим, чтобы новые тексты из SYSTEM_TEXTS
# вступили в силу.
STALE_KEYS = [
    "bot.welcome",
    "check.no_credits",
    "notify.check_done",
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM bot_content WHERE key IN :keys"
        ).bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": STALE_KEYS},
    )


def downgrade() -> None:
    # Восстанавливать старые override'ы мы не умеем и не хотим.
    pass
