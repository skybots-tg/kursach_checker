import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Broadcast, BroadcastStatus, User

logger = logging.getLogger(__name__)


async def _send_one_msg(bot: Bot, chat_id: int, msg: dict) -> bool:
    try:
        mtype = msg.get("message_type", "text")
        text = msg.get("text") or ""
        pm = msg.get("parse_mode") if text else None
        fp = msg.get("file_path")
        f_in = FSInputFile(fp) if fp and Path(fp).exists() else None

        if mtype == "text":
            if text:
                await bot.send_message(chat_id, text, parse_mode=pm)
                return True
        elif mtype == "photo" and f_in:
            await bot.send_photo(chat_id, f_in, caption=text or None, parse_mode=pm)
            return True
        elif mtype == "video" and f_in:
            await bot.send_video(chat_id, f_in, caption=text or None, parse_mode=pm)
            return True
        elif mtype == "document" and f_in:
            await bot.send_document(chat_id, f_in, caption=text or None, parse_mode=pm)
            return True
        elif mtype == "audio" and f_in:
            await bot.send_audio(chat_id, f_in, caption=text or None, parse_mode=pm)
            return True
        elif mtype == "animation" and f_in:
            await bot.send_animation(chat_id, f_in, caption=text or None, parse_mode=pm)
            return True
        elif text:
            await bot.send_message(chat_id, text, parse_mode=pm)
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


async def run_broadcast(broadcast_id: int, messages: list[dict]) -> None:
    if not settings.telegram_bot_token:
        return
    bot = Bot(token=settings.telegram_bot_token)
    try:
        async with SessionLocal() as db:
            users = list(await db.scalars(select(User)))

        sent = 0
        failed = 0
        for user in users:
            ok = True
            for msg in messages:
                if not await _send_one_msg(bot, user.telegram_id, msg):
                    ok = False
                    break
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
