"""Seed the customer-approved menu structure and message content.

Идемпотентно создаёт/обновляет 6 корневых пунктов меню по их ``payload``
(стабильный идентификатор) и заменяет их сообщения новой версией текстов,
которые заказчик прислал 16.04.2026.

Revision ID: 0012_content_rebrand
Revises: 0011_broadcast_segments
Create Date: 2026-04-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_content_rebrand"
down_revision = "0011_broadcast_segments"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Контент от заказчика (HTML-разметка для Telegram).
# ---------------------------------------------------------------------------

FLOW_CHECK_TEXT = (
    "К<b>идай файл 👇🏼</b>\n"
    "\n"
    "<blockquote>проверю и помогу привести оформление в порядок по ГОСТу</blockquote>\n"
    "\n"
    "поля, интервалы, нумерация, структура — всё, на чем обычно ловят перед сдачей\n"
    "\n"
    "<b>загружай, посмотрим что у тебя там 🔥</b>"
)

FLOW_HOW_TEXT = (
    "<b>Как работает бот? всё просто:</b>\n"
    "<blockquote>1️⃣ загружаешь файл\n"
    "2️⃣ бот проверяет и помогает с оформлением\n"
    "3️⃣ смотришь результат и решаешь, что делать дальше</blockquote>\n"
    "\n"
    "<b>🎁 у тебя есть 3 бесплатные проверки</b> — можешь спокойно протестить)\n"
    "\n"
    "<b>\n"
    "что делает наша система 👇🏼</b>\n"
    "<blockquote>➡️ быстро приводит работу в аккуратный, понятный вид по ГОСТу  \n"
    "➡️ выравнивает текст, абзацы и отступы  \n"
    "➡️ настраивает шрифт, интервалы и структуру документа  \n"
    "➡️ убирает визуальный хаос, чтобы работа выглядела собранно и профессионально</blockquote>\n"
    "\n"
    "и самое приятное: всё это занимает буквально несколько секунд! \n"
    "ты <b>сразу получаешь готовый файл</b>, <b>скачиваешь</b> его и <b>не тратишь время</b> на ручную возню 🔥\n"
    "\n"
    "если после проверки ты видишь, что нужно докрутить или есть сомнения — просто напиши нам)\n"
    "\n"
    "<b>подскажем, что поправить или поможем довести работу до идеального вида 🔥</b>\n"
    "@kursach_d"
)

FLOW_ORDER_TEXT = (
    "<b>Честно? оформление это только вершина айсберга 👀</b>\n"
    "\n"
    "<b>если у тебя:</b>\n"
    "— не готова работа\n"
    "— не проходит антиплагиат\n"
    "— горят сроки\n"
    "— или просто нет времени разбираться\n"
    "\n"
    "<blockquote>мы можем помочь полностью: от доработки до готового результата</blockquote>\n"
    "\n"
    "<b>напиши, посмотрим твою ситуацию и скажем, как лучше сделать 🔥</b>\n"
    "@kursach_d"
)

FLOW_USEFUL_TEXT = (
    "<b>хочешь сначала посмотреть, сколько студентов уже доверили нам свои работы? 👇🏼</b>\n"
    "\n"
    "этот канал — живое доказательство того, что <b>нам доверяют уже 1 000+ студентов</b>:\n"
    "<blockquote>👉🏼 курсовые\n"
    "👉🏼 дипломы\n"
    "👉🏼 доработки\n"
    "👉🏼 помощь с антиплагиатом\n"
    "👉🏼 срочные задачи</blockquote>\n"
    "\n"
    "<b><u>здесь собраны реальные отзывы, результаты и обратная связь от тех, кто уже прошел этот путь с нами 💬</u></b>\n"
    "@kursach_otzyv"
)

FLOW_REFERRAL_TEXT = (
    "<b>спаси друга от ночного кошмара с оформлением 👇🏼</b>\n"
    "\n"
    "если у тебя есть друг, который тоже мучается с курсовой, дипломом или любым другим документом — <b>отправь ему этого бота</b>\n"
    "\n"
    "за каждое такое спасение ты<b> получаешь +2 использования бесплатно </b>🔥\n"
    "\n"
    "<b>логика простая:</b>\n"
    "<blockquote>👉🏼 отправляешь бота другу\n"
    "👉🏼 друг заходит и начинает пользоваться\n"
    "👉🏼 тебе начисляется +2 бесплатные проверки</blockquote>\n"
    "\n"
    "<b>приятно и тебе, и ему:</b>\n"
    "ты получаешь бонус, а друг — шанс быстро привести работу в порядок без лишней возни\n"
    "\n"
    "<b><u>зови друга и забирай свои +2 использования 🚀</u></b>\n"
    "https://t.me/referalnaya_KURSACH_DIPLOM_bot"
)


# (payload, title, icon, row, col, text) — порядок = порядок отображения в меню.
MENU_ITEMS: list[tuple[str, str, str | None, int, int, str | None]] = [
    ("flow_check",    "Оформить работу",             "📝", 0, 0, FLOW_CHECK_TEXT),
    ("flow_how",      "Как это работает",            "⚙️", 1, 0, FLOW_HOW_TEXT),
    ("flow_order",    "Заказать полноценную работу", "💎", 2, 0, FLOW_ORDER_TEXT),
    ("flow_reviews",  "Отзывы",                      "💬", 3, 0, None),
    ("flow_useful",   "Польза для студентов",        "🎁", 3, 1, FLOW_USEFUL_TEXT),
    ("flow_referral", "Реферальная программа",       "👥", 4, 0, FLOW_REFERRAL_TEXT),
]


def upgrade() -> None:
    bind = op.get_bind()

    menu_items = sa.table(
        "content_menu_items",
        sa.column("id", sa.Integer),
        sa.column("parent_id", sa.Integer),
        sa.column("title", sa.String),
        sa.column("icon", sa.String),
        sa.column("item_type", sa.String),
        sa.column("payload", sa.Text),
        sa.column("position", sa.Integer),
        sa.column("row", sa.Integer),
        sa.column("col", sa.Integer),
        sa.column("active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    messages = sa.table(
        "menu_item_messages",
        sa.column("id", sa.Integer),
        sa.column("menu_item_id", sa.Integer),
        sa.column("position", sa.Integer),
        sa.column("message_type", sa.String),
        sa.column("text", sa.Text),
        sa.column("parse_mode", sa.String),
        sa.column("file_path", sa.String),
        sa.column("file_name", sa.String),
        sa.column("mime_type", sa.String),
        sa.column("cached_chat_id", sa.Integer),
        sa.column("cached_message_id", sa.Integer),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    for payload, title, icon, row, col, text in MENU_ITEMS:
        position = row * 100 + col
        existing_id = bind.execute(
            sa.text(
                "SELECT id FROM content_menu_items WHERE payload = :p LIMIT 1"
            ),
            {"p": payload},
        ).scalar()

        if existing_id is None:
            result = bind.execute(
                sa.insert(menu_items).values(
                    parent_id=None,
                    title=title,
                    icon=icon,
                    item_type="text",
                    payload=payload,
                    position=position,
                    row=row,
                    col=col,
                    active=True,
                    created_at=sa.func.now(),
                    updated_at=sa.func.now(),
                ).returning(menu_items.c.id)
            )
            item_id = result.scalar_one()
        else:
            item_id = existing_id
            bind.execute(
                sa.update(menu_items)
                .where(menu_items.c.id == item_id)
                .values(
                    parent_id=None,
                    title=title,
                    icon=icon,
                    item_type="text",
                    payload=payload,
                    position=position,
                    row=row,
                    col=col,
                    active=True,
                    updated_at=sa.func.now(),
                )
            )

        bind.execute(
            sa.delete(messages).where(messages.c.menu_item_id == item_id)
        )

        if text is not None:
            bind.execute(
                sa.insert(messages).values(
                    menu_item_id=item_id,
                    position=0,
                    message_type="text",
                    text=text,
                    parse_mode="HTML",
                    file_path=None,
                    file_name=None,
                    mime_type=None,
                    cached_chat_id=None,
                    cached_message_id=None,
                    created_at=sa.func.now(),
                    updated_at=sa.func.now(),
                )
            )

    # Все прочие корневые пункты, которые были в меню до правок заказчика,
    # деактивируем — так админ сможет увидеть их в админке и удалить вручную,
    # не потеряв данные.
    known_payloads = [p for p, *_ in MENU_ITEMS]
    bind.execute(
        sa.text(
            """
            UPDATE content_menu_items
            SET active = FALSE, updated_at = NOW()
            WHERE parent_id IS NULL
              AND (payload IS NULL OR payload NOT IN :known)
            """
        ).bindparams(sa.bindparam("known", expanding=True)),
        {"known": known_payloads},
    )


def downgrade() -> None:
    bind = op.get_bind()
    known_payloads = [p for p, *_ in MENU_ITEMS]

    bind.execute(
        sa.text(
            """
            DELETE FROM menu_item_messages
            WHERE menu_item_id IN (
                SELECT id FROM content_menu_items
                WHERE payload IN :known
            )
            """
        ).bindparams(sa.bindparam("known", expanding=True)),
        {"known": known_payloads},
    )
    bind.execute(
        sa.text(
            "DELETE FROM content_menu_items WHERE payload IN :known"
        ).bindparams(sa.bindparam("known", expanding=True)),
        {"known": known_payloads},
    )
