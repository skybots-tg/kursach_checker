"""Background checker for blocked / deleted Telegram users."""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound, TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.analytics import UserStatus
from app.models.entities import User
from app.services.analytics.tracker import mark_blocked, mark_deleted

logger = logging.getLogger(__name__)


async def check_user_reachable(bot: Bot, telegram_id: int) -> str:
    """Probe whether a Telegram user can receive messages.

    Returns one of: "ok", "blocked", "deleted", "error".
    """
    try:
        await bot.send_chat_action(chat_id=telegram_id, action="typing")
        return "ok"
    except TelegramForbiddenError:
        return "blocked"
    except TelegramNotFound:
        return "deleted"
    except TelegramBadRequest as exc:
        msg = str(exc).lower()
        if "user is deactivated" in msg:
            return "deleted"
        if "bot was blocked" in msg or "forbidden" in msg:
            return "blocked"
        logger.warning("TelegramBadRequest for %s: %s", telegram_id, exc)
        return "error"
    except Exception:
        logger.exception("Unexpected error checking user %s", telegram_id)
        return "error"


async def scan_all_users(bot: Bot, batch_size: int = 50) -> dict:
    """Scan all users and update their blocked/deleted status.

    Returns summary counters.
    """
    stats = {"checked": 0, "ok": 0, "blocked": 0, "deleted": 0, "errors": 0}

    async with SessionLocal() as db:
        users = (
            await db.execute(select(User.id, User.telegram_id))
        ).all()

    for user_id, telegram_id in users:
        result = await check_user_reachable(bot, telegram_id)
        stats["checked"] += 1

        if result == "blocked":
            await mark_blocked(user_id)
            stats["blocked"] += 1
        elif result == "deleted":
            await mark_deleted(user_id)
            stats["deleted"] += 1
        elif result == "ok":
            stats["ok"] += 1
        else:
            stats["errors"] += 1

        async with SessionLocal() as db:
            status = await db.get(UserStatus, user_id)
            if status:
                status.last_checked_at = datetime.utcnow()
                await db.commit()

    return stats
