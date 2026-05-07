"""Follow-up (дожимы) system: messages templates + per-user tracking.

Revision ID: 0021_followups
Revises: 0020_extra_buttons
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0021_followups"
down_revision = "0020_extra_buttons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "followup_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("step", sa.Integer(), unique=True, nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("parse_mode", sa.String(16), nullable=False, server_default="HTML"),
        sa.Column("button_text", sa.String(255), nullable=True),
        sa.Column("button_url", sa.String(1024), nullable=True),
        sa.Column("photo_paths", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_album", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "user_followups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_send_at", sa.DateTime(), nullable=True),
        sa.Column("is_converted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cycle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_user_followups_user_id", "user_followups", ["user_id"])
    op.create_index("ix_user_followups_next_send_at", "user_followups", ["next_send_at"])

    # Seed default follow-up messages
    op.execute("""
        INSERT INTO followup_messages (step, delay_minutes, text, parse_mode, button_text, button_url, photo_paths, is_album, active)
        VALUES
        (1, 15,
         '<b>понимаю, оформление — это ад</b>\nГОСТы, шрифты, отступы, списки литературы, нумерация с 3-ей страницы 🤮\n\n<blockquote>забирай <b>скидку 1000 ₽</b> на заказ по промокоду «ОФОРМЛЕНИЕ 1000» в личке @kursach_d.\n\nона действует только 24 часа ‼️</blockquote>\n\n<b>мы сами всё оформим по требованиям твоего учреждения❤️</b>',
         'HTML', 'Забрать скидку', 'https://t.me/kursach_d', '[]', false, true),
        (2, 600,
         '<b>всё ещё думаешь, что в одного справишься с оформлением?</b>\n\nтогда не забудь <a href=\"https://t.me/kursach_diplom1\">подписаться <b>на наш тг-канал</b>.</a>\n\nтам мы каждый день<b> выкладываем полезные инструкции, фишки и чек-листы</b> для лёгкой учёбы:\n<blockquote>➡️  как пройти антиплагиат в 2025 году\n➡️  где искать проверенные источники для работы\n➡️  как быстро написать введение и заключение\n➡️  какие правила помогут сделать и сдать качественный диплом за неделю\n➡️  и многое другое</blockquote>',
         'HTML', 'Подписываюсь', 'https://t.me/kursach_diplom1', '["storage/followups/msg2/photo.jpg"]', false, true),
        (3, 1440,
         '<b>я больше тебе не напишу.</b>\n\nно если вдруг просто сомневаешься, то заходи<a href=\"https://t.me/kursach_otzyv\"> <b>в наш канал с отзывами</b></a> (там лежат реальные истории студентов)\n<blockquote><b>ведь мы можем написать:</b>\n👉🏼 любой вид работы — от курсовой до контрольной\n👉🏼 по любой специальности\n👉🏼 в любое учебное заведение</blockquote>\n\n<b>p.s. с нами более 90.000 студентов сказали  «я сдал(а) на отлично» 🔥</b>',
         'HTML', 'Читать отзывы', 'https://t.me/kursach_otzyv',
         '["storage/followups/msg3/photo_1.jpg","storage/followups/msg3/photo_2.jpg","storage/followups/msg3/photo_3.jpg","storage/followups/msg3/photo_4.jpg","storage/followups/msg3/photo_5.jpg","storage/followups/msg3/photo_6.jpg"]',
         true, true)
    """)


def downgrade() -> None:
    op.drop_table("user_followups")
    op.drop_table("followup_messages")
