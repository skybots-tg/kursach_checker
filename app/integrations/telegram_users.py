"""User-related helpers for the Telegram bot.

Разделено из ``telegram_bot.py`` для соблюдения лимита 500 строк.
"""

import logging
from datetime import datetime

from aiogram.types import ChatMemberUpdated, User as TgUser
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import CreditsBalance, User
from app.services.analytics.tracker import mark_blocked, mark_unblocked
from app.services.referrals import (
    link_referral,
    try_grant_bonus_for_invited,
)
from app.services.welcome_bonus import grant_welcome_bonus

logger = logging.getLogger(__name__)


async def ensure_user(
    tg_user: TgUser, *, ref_inviter_tg_id: int | None = None,
) -> int | None:
    """Создать/обновить запись пользователя.

    При создании нового пользователя и наличии валидного
    ``ref_inviter_tg_id`` — создаёт запись в ``referrals`` и СРАЗУ выдаёт
    инвайтеру реф-бонус (условие — друг зашёл в бота).

    Возвращает ``telegram_id`` инвайтера, если бонус был выдан прямо сейчас
    (чтобы вызывающая сторона могла отправить уведомление); иначе ``None``.
    """
    inviter_tg_id_to_notify: int | None = None
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
            # Приветственный бонус новому пользователю (если включён).
            await grant_welcome_bonus(db, user_id=user.id)

            if ref_inviter_tg_id and ref_inviter_tg_id != tg_user.id:
                inviter = await db.scalar(
                    select(User).where(User.telegram_id == ref_inviter_tg_id)
                )
                if inviter is not None:
                    ref = await link_referral(
                        db,
                        inviter_user_id=inviter.id,
                        invited_user_id=user.id,
                    )
                    if ref is not None:
                        granted = await try_grant_bonus_for_invited(
                            db, invited_user_id=user.id,
                        )
                        if granted is not None and inviter.telegram_id:
                            inviter_tg_id_to_notify = inviter.telegram_id
        else:
            user.first_name = tg_user.first_name
            user.username = tg_user.username
            user.last_login_at = datetime.utcnow()
        await db.commit()
    return inviter_tg_id_to_notify


async def handle_block_status(event: ChatMemberUpdated) -> None:
    """Отреагировать на блокировку/разблокировку бота пользователем."""
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
