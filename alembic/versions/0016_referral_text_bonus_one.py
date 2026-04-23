"""Update flow_referral menu text: +2 → +1 free check, entry-based trigger.

Revision ID: 0016_referral_text_bonus_one
Revises: 0015_referrals
Create Date: 2026-04-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_referral_text_bonus_one"
down_revision = "0015_referrals"
branch_labels = None
depends_on = None


FLOW_REFERRAL_TEXT_V2 = (
    "<b>спаси друга от ночного кошмара с оформлением 👇🏼</b>\n"
    "\n"
    "если у тебя есть друг, который тоже мучается с курсовой, дипломом или "
    "любым другим документом — <b>отправь ему этого бота</b>\n"
    "\n"
    "за каждое такое спасение ты<b> получаешь +1 использование бесплатно </b>🔥\n"
    "\n"
    "<b>логика простая:</b>\n"
    "<blockquote>👉🏼 отправляешь бота другу\n"
    "👉🏼 друг заходит в бота по твоей ссылке\n"
    "👉🏼 тебе сразу начисляется +1 бесплатная проверка</blockquote>\n"
    "\n"
    "<b>приятно и тебе, и ему:</b>\n"
    "ты получаешь бонус, а друг — шанс быстро привести работу в порядок без лишней возни\n"
    "\n"
    "<b><u>зови друга и забирай своё +1 использование 🚀</u></b>\n"
    "\n"
    "<b>твоя персональная ссылка:</b>\n"
    "{ref_link}"
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE menu_item_messages
            SET text = :new_text,
                cached_chat_id = NULL,
                cached_message_id = NULL,
                updated_at = NOW()
            WHERE menu_item_id IN (
                SELECT id FROM content_menu_items WHERE payload = 'flow_referral'
            )
            """
        ),
        {"new_text": FLOW_REFERRAL_TEXT_V2},
    )


def downgrade() -> None:
    # Содержательного отката нет: в 0015 задан старый вариант текста,
    # но откатывать его не требуется — перекат миграции вверх просто
    # перепишет запись актуальной версией.
    pass
