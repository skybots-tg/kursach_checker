"""Add referrals table for the referral program.

Revision ID: 0015_referrals
Revises: 0014_reset_welcome_override
Create Date: 2026-04-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_referrals"
down_revision = "0014_reset_welcome_override"
branch_labels = None
depends_on = None


# Новый текст для пункта меню flow_referral. Вместо статической ссылки
# используем плейсхолдер {ref_link}, который бот подменяет на персональную
# реф-ссылку конкретного пользователя при отправке сообщения.
FLOW_REFERRAL_TEXT_WITH_PLACEHOLDER = (
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
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "inviter_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "invited_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("bonus_granted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "bonus_amount",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    # Переводим пункт меню flow_referral на плейсхолдер {ref_link}.
    # Кэш copy_message по этим сообщениям инвалидируем — иначе бот будет
    # рассылать всем ту же неперсонализированную копию из кеша.
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
        {"new_text": FLOW_REFERRAL_TEXT_WITH_PLACEHOLDER},
    )


def downgrade() -> None:
    op.drop_table("referrals")
