import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TgUser,
)
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ContentMenuItem, CreditsBalance, MenuItemMessage, User

logger = logging.getLogger(__name__)


async def _ensure_user(tg_user: TgUser) -> None:
    """Create or update the User record from a Telegram user object."""
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


async def build_main_keyboard() -> InlineKeyboardMarkup:
    """Build the main inline keyboard from DB menu items, grouped by row/col."""
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(ContentMenuItem)
            .where(ContentMenuItem.active.is_(True))
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

    inline_keyboard = [
        keyboard_rows[r]
        for r in sorted(keyboard_rows.keys())
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def _make_button(m: ContentMenuItem) -> InlineKeyboardButton | None:
    label = f"{m.icon} {m.title}" if m.icon else m.title
    if m.item_type == "link" and m.payload:
        return InlineKeyboardButton(text=label, url=m.payload)
    callback = m.payload or f"menu_{m.id}"
    return InlineKeyboardButton(text=label, callback_data=callback)


def _fallback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать", callback_data="start")],
    ])


async def _send_menu_messages(bot: Bot, chat_id: int, menu_item_id: int) -> None:
    """Send all messages linked to a menu item, using copy_message cache."""
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(MenuItemMessage)
            .where(MenuItemMessage.menu_item_id == menu_item_id)
            .order_by(MenuItemMessage.position.asc())
        )
        messages = list(rows)

        for msg in messages:
            sent = await _try_cached_send(bot, chat_id, msg)
            if sent:
                continue
            sent_msg = await _send_new_message(bot, chat_id, msg)
            if sent_msg:
                msg.cached_chat_id = sent_msg.chat.id
                msg.cached_message_id = sent_msg.message_id

        await db.commit()


async def _try_cached_send(bot: Bot, chat_id: int, msg: MenuItemMessage) -> bool:
    """Try sending via copy_message from cache. Returns True on success."""
    if not msg.cached_chat_id or not msg.cached_message_id:
        return False
    try:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=msg.cached_chat_id,
            message_id=msg.cached_message_id,
        )
        return True
    except Exception:
        logger.debug("copy_message cache miss for msg %d, falling back", msg.id)
        msg.cached_chat_id = None
        msg.cached_message_id = None
        return False


async def _send_new_message(bot: Bot, chat_id: int, msg: MenuItemMessage) -> Message | None:
    """Send a message from scratch and return the sent Message for caching."""
    try:
        mtype = msg.message_type
        text = msg.text or ""
        parse_mode = msg.parse_mode if msg.text else None
        file_input = FSInputFile(msg.file_path) if msg.file_path and Path(msg.file_path).exists() else None

        if mtype == "text":
            if not text:
                return None
            return await bot.send_message(chat_id, text, parse_mode=parse_mode)
        if mtype == "photo" and file_input:
            return await bot.send_photo(chat_id, file_input, caption=text or None, parse_mode=parse_mode)
        if mtype == "video" and file_input:
            return await bot.send_video(chat_id, file_input, caption=text or None, parse_mode=parse_mode)
        if mtype == "audio" and file_input:
            return await bot.send_audio(chat_id, file_input, caption=text or None, parse_mode=parse_mode)
        if mtype == "document" and file_input:
            return await bot.send_document(chat_id, file_input, caption=text or None, parse_mode=parse_mode)
        if mtype == "animation" and file_input:
            return await bot.send_animation(chat_id, file_input, caption=text or None, parse_mode=parse_mode)

        if text:
            return await bot.send_message(chat_id, text, parse_mode=parse_mode)
        return None
    except Exception:
        logger.exception("Failed to send message %d to chat %d", msg.id, chat_id)
        return None


async def run_bot() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        if message.from_user:
            await _ensure_user(message.from_user)
        kb = await build_main_keyboard()
        await message.answer(
            "Добро пожаловать в сервис технической проверки документов.",
            reply_markup=kb,
        )

    @dp.callback_query(F.data.startswith("menu_"))
    async def menu_callback_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        data = callback.data or ""
        try:
            menu_item_id = int(data.split("_", 1)[1])
        except (ValueError, IndexError):
            return
        await _send_menu_messages(bot, callback.message.chat.id, menu_item_id)

    @dp.callback_query()
    async def custom_callback_handler(callback: CallbackQuery) -> None:
        """Handle callback queries with custom payload (not menu_*)."""
        await callback.answer()
        data = callback.data or ""
        item = await _find_menu_item_by_payload(data)
        if item:
            await _send_menu_messages(bot, callback.message.chat.id, item.id)

    @dp.message()
    async def fallback_message_handler(message: Message) -> None:
        """Handle any message that wasn't caught by specific handlers."""
        if message.from_user:
            await _ensure_user(message.from_user)
        kb = await build_main_keyboard()
        await message.answer(
            "Добро пожаловать в сервис технической проверки документов.",
            reply_markup=kb,
        )

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
