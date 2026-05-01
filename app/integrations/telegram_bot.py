import logging
from collections import defaultdict
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from sqlalchemy import select

from app.db.session import SessionLocal
from app.integrations.analytics_middleware import AnalyticsMiddleware
from app.integrations.telegram_bot_factory import make_bot
from app.integrations.telegram_check_handler import handle_document
from app.integrations.telegram_constants import (
    CHECK_UPLOAD_NEW_CB,
    START_ITEM_PAYLOAD,
    SUBSCRIBE_BONUS_PAYLOAD,
    SUBSCRIBE_CHECK_CB,
)
from app.integrations.telegram_extra_buttons import build_extra_buttons
from app.integrations.telegram_messages import send_content_messages
from app.integrations.telegram_notify import notify_referral_bonus
from app.integrations.telegram_subscribe import (
    build_subscribe_menu_keyboard,
    handle_subscribe_check,
)
from app.integrations.telegram_users import ensure_user, handle_block_status
from app.models import ContentMenuItem, CreditsBalance, User
from app.services.bot_texts import get_text
from app.services.referrals import parse_ref_payload

# Реэкспорт для обратной совместимости — часть кода может импортировать
# константы из этого модуля.
__all__ = ["CHECK_UPLOAD_NEW_CB", "START_ITEM_PAYLOAD", "run_bot", "build_main_keyboard"]

logger = logging.getLogger(__name__)

# chat_id → list of bot-sent message_ids (for cleanup on navigation)
_chat_messages: dict[int, list[int]] = defaultdict(list)


# ---------------------------------------------------------------------------
#  User helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
#  Message tracking & cleanup
# ---------------------------------------------------------------------------

async def _delete_tracked(bot: Bot, chat_id: int) -> None:
    """Delete all previously tracked bot messages for a chat."""
    msg_ids = _chat_messages.pop(chat_id, [])
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass


def _track(chat_id: int, *message_ids: int) -> None:
    _chat_messages[chat_id].extend(message_ids)


# ---------------------------------------------------------------------------
#  Keyboard building
# ---------------------------------------------------------------------------

def _make_button(m: ContentMenuItem) -> InlineKeyboardButton | None:
    label = f"{m.icon} {m.title}" if m.icon else m.title
    if m.item_type == "link" and m.payload:
        return InlineKeyboardButton(text=label, url=m.payload)
    callback = m.payload or f"menu_{m.id}"
    return InlineKeyboardButton(text=label, callback_data=callback)


def _fallback_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Начать")]],
        resize_keyboard=True,
        is_persistent=True,
    )


def _root_item_label(item: ContentMenuItem) -> str:
    return f"{item.icon} {item.title}" if item.icon else item.title


async def _get_item_depth(db, item: ContentMenuItem) -> int:
    """Count the number of ancestors (0 = root item)."""
    depth = 0
    current_parent_id = item.parent_id
    while current_parent_id is not None:
        depth += 1
        parent = await db.get(ContentMenuItem, current_parent_id)
        if parent is None:
            break
        current_parent_id = parent.parent_id
    return depth


async def _build_children_rows(
    db, parent_id: int,
) -> list[list[InlineKeyboardButton]]:
    """Build inline-keyboard rows from active children of *parent_id*."""
    rows = await db.scalars(
        select(ContentMenuItem)
        .where(
            ContentMenuItem.active.is_(True),
            ContentMenuItem.parent_id == parent_id,
        )
        .order_by(ContentMenuItem.row.asc(), ContentMenuItem.col.asc())
    )
    items = list(rows)
    if not items:
        return []

    keyboard_rows: dict[int, list[InlineKeyboardButton]] = {}
    for m in items:
        btn = _make_button(m)
        if btn:
            keyboard_rows.setdefault(m.row, []).append(btn)

    return [keyboard_rows[r] for r in sorted(keyboard_rows.keys())]


def _nav_row(parent_id: int | None, depth: int) -> list[InlineKeyboardButton]:
    """Build the navigation row (back / main menu) based on depth."""
    row: list[InlineKeyboardButton] = []

    if parent_id is not None:
        row.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"menu_{parent_id}",
            ),
        )
    else:
        row.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data="nav_home"),
        )

    if depth >= 2:
        row.append(
            InlineKeyboardButton(
                text="🏠 Главное меню", callback_data="nav_home",
            ),
        )

    return row


async def _load_root_items() -> list[ContentMenuItem]:
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(ContentMenuItem)
            .where(
                ContentMenuItem.active.is_(True),
                ContentMenuItem.parent_id.is_(None),
                (ContentMenuItem.payload.is_(None))
                | (ContentMenuItem.payload != START_ITEM_PAYLOAD),
            )
            .order_by(ContentMenuItem.row.asc(), ContentMenuItem.col.asc())
        )
        return list(rows)


async def build_main_keyboard() -> ReplyKeyboardMarkup:
    """Build the root-level reply keyboard (bottom menu, persistent)."""
    items = await _load_root_items()
    if not items:
        return _fallback_reply_keyboard()

    keyboard_rows: dict[int, list[KeyboardButton]] = {}
    for m in items:
        keyboard_rows.setdefault(m.row, []).append(
            KeyboardButton(text=_root_item_label(m)),
        )

    if not keyboard_rows:
        return _fallback_reply_keyboard()

    return ReplyKeyboardMarkup(
        keyboard=[keyboard_rows[r] for r in sorted(keyboard_rows.keys())],
        resize_keyboard=True,
        is_persistent=True,
    )


async def _send_kb_anchor(bot: Bot, chat_id: int) -> int | None:
    """Отправить «якорное» сообщение с reply-клавиатурой главного меню.

    В Telegram reply-клавиатура (нижнее меню) привязана к конкретному
    сообщению: пока это сообщение существует — клавиатура видна, удалили
    его — клавиатура исчезает. Чтобы меню «всегда было внизу», после
    каждой навигации мы шлём короткое сообщение-якорь с пристёгнутой
    ``ReplyKeyboardMarkup``. Якорь трекается как обычное сообщение и
    удаляется на следующем шаге — вместо него тут же отправляется новый,
    так что в чате всегда есть ровно один актуальный якорь внизу.
    """
    kb = await build_main_keyboard()
    text = await get_text("bot.kb_anchor")
    try:
        sent = await bot.send_message(
            chat_id, text, reply_markup=kb, parse_mode="HTML",
        )
    except Exception:
        logger.exception("Failed to send kb anchor to chat %d", chat_id)
        return None
    return sent.message_id


async def _find_root_item_by_label(text: str) -> ContentMenuItem | None:
    """Match user text against active root menu items (label = icon + title)."""
    items = await _load_root_items()
    for item in items:
        if _root_item_label(item) == text:
            return item
    return None


# ---------------------------------------------------------------------------
#  Navigation
# ---------------------------------------------------------------------------

async def _get_start_item_id() -> int | None:
    """Return id of the reserved ``__start__`` menu item, if it exists and is active."""
    async with SessionLocal() as db:
        return await db.scalar(
            select(ContentMenuItem.id).where(
                ContentMenuItem.payload == START_ITEM_PAYLOAD,
                ContentMenuItem.active.is_(True),
            )
        )


async def _navigate_home(
    bot: Bot, chat_id: int, tg_user_id: int | None = None,
) -> None:
    """Delete tracked messages and show the main (root) menu.

    Порядок:
    1. Сообщения служебного пункта ``__start__`` (если есть) — например
       видео-кружок, прикреплённый к /start через админку.
    2. Приветствие ``bot.welcome`` с главной клавиатурой как последнее
       сообщение (чтобы именно к нему крепилось меню).
    """
    await _delete_tracked(bot, chat_id)
    sent_ids: list[int] = []

    start_item_id = await _get_start_item_id()
    if start_item_id is not None:
        ids = await send_content_messages(
            bot, chat_id, start_item_id, reply_markup=None,
            tg_user_id=tg_user_id,
        )
        sent_ids.extend(ids)

    kb = await build_main_keyboard()
    welcome = await get_text("bot.welcome")
    sent = await bot.send_message(
        chat_id, welcome, reply_markup=kb, parse_mode="HTML",
    )
    sent_ids.append(sent.message_id)

    _track(chat_id, *sent_ids)


async def _send_upload_prompt(bot: Bot, chat_id: int, tg_user_id: int) -> None:
    """Показать пользователю приглашение загрузить новый файл со счётчиком попыток."""
    await _delete_tracked(bot, chat_id)

    credits_value = 0
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.telegram_id == tg_user_id))
        if user:
            balance = await db.get(CreditsBalance, user.id)
            if balance:
                credits_value = balance.credits_available

    text = await get_text("check.upload_prompt", credits=credits_value)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav_home")],
        ]
    )
    sent = await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)
    _track(chat_id, sent.message_id)

    anchor_id = await _send_kb_anchor(bot, chat_id)
    if anchor_id is not None:
        _track(chat_id, anchor_id)


async def _handle_root_item_tap(
    bot: Bot, chat_id: int, item: ContentMenuItem,
    tg_user_id: int | None = None,
) -> None:
    """Handle a reply-keyboard tap on a top-level menu item."""
    if item.item_type == "link" and item.payload:
        await _delete_tracked(bot, chat_id)
        link_kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text=_root_item_label(item), url=item.payload,
                ),
            ]],
        )
        sent = await bot.send_message(
            chat_id, _root_item_label(item), reply_markup=link_kb,
        )
        _track(chat_id, sent.message_id)
        anchor_id = await _send_kb_anchor(bot, chat_id)
        if anchor_id is not None:
            _track(chat_id, anchor_id)
        return
    await _navigate_to_item(bot, chat_id, item.id, tg_user_id=tg_user_id)


async def _navigate_to_item(
    bot: Bot, chat_id: int, menu_item_id: int,
    tg_user_id: int | None = None,
) -> None:
    """Full navigation: delete old messages → send content → attach keyboard."""
    await _delete_tracked(bot, chat_id)

    async with SessionLocal() as db:
        item = await db.get(ContentMenuItem, menu_item_id)
        if not item or not item.active:
            await _navigate_home(bot, chat_id, tg_user_id=tg_user_id)
            return

        depth = await _get_item_depth(db, item)
        parent_id = item.parent_id
        item_title = item.title
        item_payload = item.payload
        item_extra_buttons = list(item.extra_buttons or [])
        children_rows = await _build_children_rows(db, menu_item_id)

    inline_keyboard: list[list[InlineKeyboardButton]] = list(children_rows)

    # Пункт «получи +N за подписку на канал» — стандартных дочерних
    # пунктов у него нет, мы подмешиваем кнопки «Перейти в канал» и
    # «Проверить подписку» из спецклавиатуры.
    if item_payload == SUBSCRIBE_BONUS_PAYLOAD:
        subscribe_kb = await build_subscribe_menu_keyboard()
        if subscribe_kb is not None:
            inline_keyboard.extend(subscribe_kb.inline_keyboard)

    # Дополнительные inline-кнопки, включённые свитчами в админке
    # (поле ContentMenuItem.extra_buttons): «Проверить подписку»,
    # «Оплатить», «Пригласить друга» и т.п.
    if item_extra_buttons:
        inline_keyboard.extend(await build_extra_buttons(item_extra_buttons))

    inline_keyboard.append(_nav_row(parent_id, depth))
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    sent_ids = await send_content_messages(
        bot, chat_id, menu_item_id, reply_markup=keyboard,
        tg_user_id=tg_user_id,
    )

    if not sent_ids:
        sent = await bot.send_message(
            chat_id, f"📋 {item_title}", reply_markup=keyboard,
        )
        sent_ids.append(sent.message_id)

    anchor_id = await _send_kb_anchor(bot, chat_id)
    if anchor_id is not None:
        sent_ids.append(anchor_id)

    _track(chat_id, *sent_ids)


# ---------------------------------------------------------------------------
#  Bot setup & handlers
# ---------------------------------------------------------------------------

async def run_bot() -> None:
    bot = make_bot()
    dp = Dispatcher()
    dp.message.middleware(AnalyticsMiddleware())
    dp.callback_query.middleware(AnalyticsMiddleware())

    @dp.my_chat_member()
    async def chat_member_handler(event: ChatMemberUpdated) -> None:
        await handle_block_status(event)

    @dp.message(CommandStart())
    async def start_handler(
        message: Message, command: CommandObject,
    ) -> None:
        ref_inviter_tg_id: int | None = None
        inviter_id = parse_ref_payload(command.args)
        if inviter_id:
            ref_inviter_tg_id = inviter_id

        inviter_to_notify: int | None = None
        if message.from_user:
            inviter_to_notify = await ensure_user(
                message.from_user,
                ref_inviter_tg_id=ref_inviter_tg_id,
            )

        tg_user_id = message.from_user.id if message.from_user else None
        await _navigate_home(bot, message.chat.id, tg_user_id=tg_user_id)

        if inviter_to_notify is not None:
            await notify_referral_bonus(inviter_to_notify)

    @dp.callback_query(F.data == "nav_home")
    async def home_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        tg_user_id = callback.from_user.id if callback.from_user else None
        await _navigate_home(
            bot, callback.message.chat.id, tg_user_id=tg_user_id,
        )

    @dp.callback_query(F.data == CHECK_UPLOAD_NEW_CB)
    async def upload_new_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if not callback.from_user:
            return
        await _send_upload_prompt(
            bot, callback.message.chat.id, callback.from_user.id,
        )

    @dp.callback_query(F.data == SUBSCRIBE_CHECK_CB)
    async def subscribe_check_callback_handler(
        callback: CallbackQuery,
    ) -> None:
        await callback.answer()
        if not callback.from_user or not callback.message:
            return
        await handle_subscribe_check(
            bot,
            chat_id=callback.message.chat.id,
            tg_user_id=callback.from_user.id,
            track=lambda c, m: _track(c, m),
        )

    @dp.callback_query(F.data.startswith("menu_"))
    async def menu_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data or ""
        try:
            menu_item_id = int(data.split("_", 1)[1])
        except (ValueError, IndexError):
            return
        tg_user_id = callback.from_user.id if callback.from_user else None
        await _navigate_to_item(
            bot, callback.message.chat.id, menu_item_id,
            tg_user_id=tg_user_id,
        )

    @dp.callback_query()
    async def custom_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data or ""
        item = await _find_menu_item_by_payload(data)
        if item:
            tg_user_id = callback.from_user.id if callback.from_user else None
            await _navigate_to_item(
                bot, callback.message.chat.id, item.id,
                tg_user_id=tg_user_id,
            )

    @dp.message(F.document)
    async def document_handler(message: Message) -> None:
        if message.from_user:
            await ensure_user(message.from_user)
        await handle_document(message, bot)

    @dp.message()
    async def fallback_message_handler(message: Message) -> None:
        if message.from_user:
            await ensure_user(message.from_user)
        tg_user_id = message.from_user.id if message.from_user else None
        text = (message.text or "").strip()
        if text:
            item = await _find_root_item_by_label(text)
            if item is not None:
                await _handle_root_item_tap(
                    bot, message.chat.id, item, tg_user_id=tg_user_id,
                )
                return
        await _navigate_home(bot, message.chat.id, tg_user_id=tg_user_id)

    await dp.start_polling(bot)


async def _find_menu_item_by_payload(payload: str) -> ContentMenuItem | None:
    if not payload:
        return None
    async with SessionLocal() as db:
        return await db.scalar(
            select(ContentMenuItem)
            .where(ContentMenuItem.payload == payload, ContentMenuItem.active.is_(True))
            .limit(1)
        )
