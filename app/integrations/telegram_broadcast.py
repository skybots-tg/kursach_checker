import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.telegram_bot_factory import make_bot
from app.models import Broadcast, BroadcastStatus

logger = logging.getLogger(__name__)


def _build_keyboard(buttons_json: list | None) -> InlineKeyboardMarkup | None:
    if not buttons_json:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for btn in buttons_json:
        text = btn.get("text", "")
        url = btn.get("url", "")
        if not text or not url:
            continue
        ib = InlineKeyboardButton(text=text, url=url)
        if btn.get("same_row") and current_row:
            current_row.append(ib)
        else:
            if current_row:
                rows.append(current_row)
            current_row = [ib]
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def _make_input_media(media_type: str, file_input: FSInputFile, caption: str | None = None, parse_mode: str | None = None):
    kwargs: dict = {"media": file_input}
    if caption:
        kwargs["caption"] = caption
        if parse_mode:
            kwargs["parse_mode"] = parse_mode
    if media_type == "photo":
        return InputMediaPhoto(**kwargs)
    if media_type == "video":
        return InputMediaVideo(**kwargs)
    if media_type == "animation":
        return InputMediaAnimation(**kwargs)
    if media_type == "audio":
        return InputMediaAudio(**kwargs)
    return InputMediaDocument(**kwargs)


async def _send_to_user(
    bot: Bot,
    chat_id: int,
    messages: list[dict],
    files: list[dict],
) -> bool:
    """Send a complete broadcast to one user. Returns True on success."""
    try:
        keyboard = None
        text = ""
        parse_mode = None
        if messages:
            msg = messages[0]
            text = msg.get("text") or ""
            parse_mode = msg.get("parse_mode") if text else None
            keyboard = _build_keyboard(msg.get("buttons_json"))

        valid_files = [
            f for f in files
            if f.get("file_path") and Path(f["file_path"]).exists()
        ]

        if len(valid_files) >= 2:
            media_items = []
            for i, f in enumerate(valid_files):
                fi = FSInputFile(f["file_path"])
                cap = text if i == 0 else None
                pm = parse_mode if i == 0 else None
                media_items.append(
                    _make_input_media(f.get("media_type", "document"), fi, cap, pm)
                )
            await bot.send_media_group(chat_id, media=media_items)
            if keyboard:
                btn_text = "\u200B"
                await bot.send_message(chat_id, btn_text, reply_markup=keyboard)
            return True

        if len(valid_files) == 1:
            f = valid_files[0]
            fi = FSInputFile(f["file_path"])
            mt = f.get("media_type", "document")
            cap = text or None
            pm = parse_mode if cap else None
            if mt == "photo":
                await bot.send_photo(chat_id, fi, caption=cap, parse_mode=pm, reply_markup=keyboard)
            elif mt == "video":
                await bot.send_video(chat_id, fi, caption=cap, parse_mode=pm, reply_markup=keyboard)
            elif mt == "animation":
                await bot.send_animation(chat_id, fi, caption=cap, parse_mode=pm, reply_markup=keyboard)
            elif mt == "audio":
                await bot.send_audio(chat_id, fi, caption=cap, parse_mode=pm, reply_markup=keyboard)
            elif mt == "video_note":
                await bot.send_video_note(chat_id, fi)
                if text:
                    await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=keyboard)
            else:
                await bot.send_document(chat_id, fi, caption=cap, parse_mode=pm, reply_markup=keyboard)
            return True

        if text:
            await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=keyboard)
            return True

        return False
    except Exception:
        logger.debug("Broadcast msg failed for chat %d", chat_id)
        return False


async def _update_progress(broadcast_id: int, sent: int, failed: int) -> None:
    async with SessionLocal() as db:
        b = await db.get(Broadcast, broadcast_id)
        if b:
            b.sent_count = sent
            b.failed_count = failed
            await db.commit()


async def run_broadcast(
    broadcast_id: int,
    messages: list[dict],
    files: list[dict],
    telegram_ids: list[int] | None = None,
) -> None:
    if not settings.telegram_bot_token:
        return
    bot = make_bot()
    try:
        if telegram_ids is not None:
            tg_ids = telegram_ids
        else:
            from app.models import User
            async with SessionLocal() as db:
                users = list(await db.scalars(select(User)))
            tg_ids = [u.telegram_id for u in users]

        sent = 0
        failed = 0
        for tg_id in tg_ids:
            ok = await _send_to_user(bot, tg_id, messages, files)
            if ok:
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(0.05)
            if (sent + failed) % 50 == 0:
                await _update_progress(broadcast_id, sent, failed)

        async with SessionLocal() as db:
            b = await db.get(Broadcast, broadcast_id)
            if b:
                b.sent_count = sent
                b.failed_count = failed
                b.status = BroadcastStatus.sent
                b.sent_at = datetime.utcnow()
                await db.commit()
    except Exception:
        logger.exception("Broadcast %d failed", broadcast_id)
        async with SessionLocal() as db:
            b = await db.get(Broadcast, broadcast_id)
            if b:
                b.status = BroadcastStatus.failed
                await db.commit()
    finally:
        await bot.session.close()


async def test_send_broadcast(
    messages: list[dict],
    files: list[dict],
    telegram_ids: list[int],
) -> dict:
    if not settings.telegram_bot_token:
        return {"sent": 0, "failed": 0}
    bot = make_bot()
    try:
        sent = 0
        failed = 0
        for tg_id in telegram_ids:
            ok = await _send_to_user(bot, tg_id, messages, files)
            sent += 1 if ok else 0
            failed += 0 if ok else 1
            await asyncio.sleep(0.05)
        return {"sent": sent, "failed": failed}
    finally:
        await bot.session.close()
