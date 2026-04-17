import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TgUser,
)
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.analytics_middleware import AnalyticsMiddleware
from app.integrations.telegram_check_handler import handle_document
from app.integrations.telegram_constants import (
    CHECK_UPLOAD_NEW_CB,
    START_ITEM_PAYLOAD,
)
from app.models import ContentMenuItem, CreditsBalance, MenuItemMessage, User
from app.services.analytics.tracker import mark_blocked, mark_unblocked
from app.services.bot_texts import get_text

# Реэкспорт для обратной совместимости — часть кода может импортировать
# константы из этого модуля.
__all__ = ["CHECK_UPLOAD_NEW_CB", "START_ITEM_PAYLOAD", "run_bot", "build_main_keyboard"]

logger = logging.getLogger(__name__)

# chat_id → list of bot-sent message_ids (for cleanup on navigation)
_chat_messages: dict[int, list[int]] = defaultdict(list)


# ---------------------------------------------------------------------------
#  User helpers
# ---------------------------------------------------------------------------

async def _ensure_user(tg_user: TgUser) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(
            select(User).where(User.telegram_id == tg_user.id)
        )
        if user is None:
            user = User(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name,
                username=tg_user.username,
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
            await db.flush()
            db.add(CreditsBalance(user_id=user.id, credits_available=0))
        else:
            user.first_name = tg_user.first_name
            user.username = tg_user.username
            user.last_login_at = datetime.utcnow()
        await db.commit()


async def _handle_block_status(event: ChatMemberUpdated) -> None:
    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    tg_id = event.from_user.id

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.telegram_id == tg_id))
        if not user:
            return
        user_id = user.id

    if new_status == "kicked":
        await mark_blocked(user_id)
        logger.info("User %d (tg=%d) blocked the bot", user_id, tg_id)
    elif new_status == "member" and old_status == "kicked":
        await mark_unblocked(user_id)
        logger.info("User %d (tg=%d) unblocked the bot", user_id, tg_id)


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


def _fallback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать", callback_data="nav_home")],
    ])


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


async def build_main_keyboard() -> InlineKeyboardMarkup:
    """Build the root-level inline keyboard (only top-level items)."""
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
        items = list(rows)

    if not items:
        return _fallback_keyboard()

    keyboard_rows: dict[int, list[InlineKeyboardButton]] = {}
    for m in items:
        btn = _make_button(m)
        if btn:
            keyboard_rows.setdefault(m.row, []).append(btn)

    if not keyboard_rows:
        return _fallback_keyboard()

    return InlineKeyboardMarkup(
        inline_keyboard=[keyboard_rows[r] for r in sorted(keyboard_rows.keys())],
    )


# ---------------------------------------------------------------------------
#  Message sending
# ---------------------------------------------------------------------------

async def _try_cached_send(
    bot: Bot,
    chat_id: int,
    msg: MenuItemMessage,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int | None:
    """Try copy_message from cache. Returns sent message_id or None."""
    if not msg.cached_chat_id or not msg.cached_message_id:
        return None
    try:
        result = await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=msg.cached_chat_id,
            message_id=msg.cached_message_id,
            reply_markup=reply_markup,
        )
        return result.message_id
    except Exception:
        logger.debug("copy_message cache miss for msg %d", msg.id)
        msg.cached_chat_id = None
        msg.cached_message_id = None
        return None


async def _send_new_message(
    bot: Bot,
    chat_id: int,
    msg: MenuItemMessage,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message | None:
    """Send a message from scratch and return the sent Message for caching."""
    try:
        mtype = msg.message_type
        text = msg.text or ""
        parse_mode = msg.parse_mode if msg.text else None
        file_input = (
            FSInputFile(msg.file_path)
            if msg.file_path and Path(msg.file_path).exists()
            else None
        )

        kw: dict = {}
        if reply_markup:
            kw["reply_markup"] = reply_markup

        if mtype == "text":
            if not text:
                return None
            return await bot.send_message(
                chat_id, text, parse_mode=parse_mode, **kw,
            )
        if mtype == "photo" and file_input:
            return await bot.send_photo(
                chat_id, file_input, caption=text or None,
                parse_mode=parse_mode, **kw,
            )
        if mtype == "video" and file_input:
            return await bot.send_video(
                chat_id, file_input, caption=text or None,
                parse_mode=parse_mode, **kw,
            )
        if mtype == "audio" and file_input:
            return await bot.send_audio(
                chat_id, file_input, caption=text or None,
                parse_mode=parse_mode, **kw,
            )
        if mtype == "document" and file_input:
            return await bot.send_document(
                chat_id, file_input, caption=text or None,
                parse_mode=parse_mode, **kw,
            )
        if mtype == "animation" and file_input:
            return await bot.send_animation(
                chat_id, file_input, caption=text or None,
                parse_mode=parse_mode, **kw,
            )
        if mtype == "video_note" and file_input:
            # У video_note нет подписи и parse_mode, см. Telegram Bot API.
            return await bot.send_video_note(chat_id, file_input, **kw)
        if text:
            return await bot.send_message(
                chat_id, text, parse_mode=parse_mode, **kw,
            )
        return None
    except Exception:
        logger.exception("Failed to send message %d to chat %d", msg.id, chat_id)
        return None


async def _send_content_messages(
    bot: Bot,
    chat_id: int,
    menu_item_id: int,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> list[int]:
    """Send all messages for a menu item.

    *reply_markup* is attached to the **last** content message.
    Returns list of sent message_ids.
    """
    sent_ids: list[int] = []

    async with SessionLocal() as db:
        rows = await db.scalars(
            select(MenuItemMessage)
            .where(MenuItemMessage.menu_item_id == menu_item_id)
            .order_by(MenuItemMessage.position.asc())
        )
        messages = list(rows)

        if not messages:
            return sent_ids

        for idx, msg in enumerate(messages):
            is_last = idx == len(messages) - 1
            markup = reply_markup if is_last else None

            cached_mid = await _try_cached_send(
                bot, chat_id, msg, reply_markup=markup,
            )
            if cached_mid is not None:
                sent_ids.append(cached_mid)
                continue

            sent_msg = await _send_new_message(
                bot, chat_id, msg, reply_markup=markup,
            )
            if sent_msg:
                msg.cached_chat_id = sent_msg.chat.id
                msg.cached_message_id = sent_msg.message_id
                sent_ids.append(sent_msg.message_id)

        await db.commit()

    return sent_ids


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


async def _navigate_home(bot: Bot, chat_id: int) -> None:
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
        ids = await _send_content_messages(
            bot, chat_id, start_item_id, reply_markup=None,
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


async def _navigate_to_item(bot: Bot, chat_id: int, menu_item_id: int) -> None:
    """Full navigation: delete old messages → send content → attach keyboard."""
    await _delete_tracked(bot, chat_id)

    async with SessionLocal() as db:
        item = await db.get(ContentMenuItem, menu_item_id)
        if not item or not item.active:
            await _navigate_home(bot, chat_id)
            return

        depth = await _get_item_depth(db, item)
        parent_id = item.parent_id
        item_title = item.title
        children_rows = await _build_children_rows(db, menu_item_id)

    inline_keyboard = list(children_rows)
    inline_keyboard.append(_nav_row(parent_id, depth))
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    sent_ids = await _send_content_messages(
        bot, chat_id, menu_item_id, reply_markup=keyboard,
    )

    if not sent_ids:
        sent = await bot.send_message(
            chat_id, f"📋 {item_title}", reply_markup=keyboard,
        )
        sent_ids.append(sent.message_id)

    _track(chat_id, *sent_ids)


# ---------------------------------------------------------------------------
#  Bot setup & handlers
# ---------------------------------------------------------------------------

async def run_bot() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.message.middleware(AnalyticsMiddleware())
    dp.callback_query.middleware(AnalyticsMiddleware())

    @dp.my_chat_member()
    async def chat_member_handler(event: ChatMemberUpdated) -> None:
        await _handle_block_status(event)

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        if message.from_user:
            await _ensure_user(message.from_user)
        await _navigate_home(bot, message.chat.id)

    @dp.callback_query(F.data == "nav_home")
    async def home_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        await _navigate_home(bot, callback.message.chat.id)

    @dp.callback_query(F.data == CHECK_UPLOAD_NEW_CB)
    async def upload_new_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if not callback.from_user:
            return
        await _send_upload_prompt(
            bot, callback.message.chat.id, callback.from_user.id,
        )

    @dp.callback_query(F.data.startswith("menu_"))
    async def menu_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data or ""
        try:
            menu_item_id = int(data.split("_", 1)[1])
        except (ValueError, IndexError):
            return
        await _navigate_to_item(bot, callback.message.chat.id, menu_item_id)

    @dp.callback_query()
    async def custom_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data or ""
        item = await _find_menu_item_by_payload(data)
        if item:
            await _navigate_to_item(bot, callback.message.chat.id, item.id)

    @dp.message(F.document)
    async def document_handler(message: Message) -> None:
        if message.from_user:
            await _ensure_user(message.from_user)
        await handle_document(message, bot)

    @dp.message()
    async def fallback_message_handler(message: Message) -> None:
        if message.from_user:
            await _ensure_user(message.from_user)
        await _navigate_home(bot, message.chat.id)

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
