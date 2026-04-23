"""Отправка сообщений пункта меню, включая персонализацию и кеш copy_message.

Вынесено из ``telegram_bot.py`` ради ограничения 500 строк на файл.
"""

from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import MenuItemMessage
from app.services.referrals import build_ref_link

logger = logging.getLogger(__name__)


REF_LINK_PLACEHOLDER = "{ref_link}"


def message_needs_personalization(msg: MenuItemMessage) -> bool:
    """True, если в тексте сообщения есть подставляемые на лету плейсхолдеры."""
    return bool(msg.text) and REF_LINK_PLACEHOLDER in msg.text


def personalize_text(text: str, *, tg_user_id: int | None) -> str:
    """Подставить персональные плейсхолдеры в текст сообщения."""
    if REF_LINK_PLACEHOLDER in text and tg_user_id:
        text = text.replace(
            REF_LINK_PLACEHOLDER, build_ref_link(tg_user_id),
        )
    return text


async def _try_cached_send(
    bot: Bot,
    chat_id: int,
    msg: MenuItemMessage,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> int | None:
    """Попробовать copy_message из кеша. Возвращает message_id или None."""
    if message_needs_personalization(msg):
        # Кэшированная копия не даст подставить персональные значения,
        # поэтому для таких сообщений кешом не пользуемся.
        return None
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
    tg_user_id: int | None = None,
) -> Message | None:
    """Отправить сообщение с нуля; результат — Message для кеширования."""
    try:
        mtype = msg.message_type
        text = msg.text or ""
        if text:
            text = personalize_text(text, tg_user_id=tg_user_id)
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
        logger.exception(
            "Failed to send message %d to chat %d", msg.id, chat_id,
        )
        return None


async def send_content_messages(
    bot: Bot,
    chat_id: int,
    menu_item_id: int,
    reply_markup: InlineKeyboardMarkup | None = None,
    tg_user_id: int | None = None,
) -> list[int]:
    """Отправить все сообщения пункта меню.

    *reply_markup* прикрепляется к ПОСЛЕДНЕМУ сообщению.
    Возвращает список отправленных message_id.
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
                tg_user_id=tg_user_id,
            )
            if sent_msg:
                if not message_needs_personalization(msg):
                    # Персонализированные сообщения кешировать нельзя —
                    # иначе все получат копию с чужой реф-ссылкой.
                    msg.cached_chat_id = sent_msg.chat.id
                    msg.cached_message_id = sent_msg.message_id
                sent_ids.append(sent_msg.message_id)

        await db.commit()

    return sent_ids
