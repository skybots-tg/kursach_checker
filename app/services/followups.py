"""Follow-up (дожимы) service — scheduling and sending reminder messages.

Логика:
- Сообщение 1 (через 15 мин) — однократно, если пользователь бездействует.
- Сообщение 2 (через 10 часов) — зацикленно с сообщением 3.
- Сообщение 3 (через 24 часа) — зацикленно с сообщением 2.
Цикл: 1 → 2 → 3 → 2 → 3 → ...
Конверсия (отправка документа) останавливает цепочку.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models import FollowUpMessage, User, UserFollowUp

logger = logging.getLogger(__name__)

# Базовая директория проекта (для резолва относительных путей к фото).
BASE_DIR = Path(__file__).resolve().parent.parent.parent


async def start_followup_chain(user_id: int) -> None:
    """Инициировать цепочку дожимов для пользователя (при /start)."""
    async with SessionLocal() as db:
        existing = await db.scalar(
            select(UserFollowUp).where(UserFollowUp.user_id == user_id)
        )
        if existing is not None:
            # Уже есть запись — не пересоздаём (повторный /start).
            return

        msg1 = await db.scalar(
            select(FollowUpMessage).where(
                FollowUpMessage.step == 1, FollowUpMessage.active.is_(True),
            )
        )
        delay = msg1.delay_minutes if msg1 else 15
        followup = UserFollowUp(
            user_id=user_id,
            current_step=0,
            next_send_at=datetime.utcnow() + timedelta(minutes=delay),
        )
        db.add(followup)
        await db.commit()
        logger.info("Follow-up chain started for user_id=%d, first send in %d min", user_id, delay)


async def mark_converted(user_id: int) -> None:
    """Пометить пользователя как конвертированного — остановить цепочку."""
    async with SessionLocal() as db:
        await db.execute(
            update(UserFollowUp)
            .where(UserFollowUp.user_id == user_id)
            .values(is_converted=True, next_send_at=None, updated_at=datetime.utcnow())
        )
        await db.commit()


async def process_pending_followups(bot: Bot) -> int:
    """Обработать все pending follow-ups. Возвращает количество отправленных."""
    now = datetime.utcnow()
    sent_count = 0

    async with SessionLocal() as db:
        rows = await db.scalars(
            select(UserFollowUp).where(
                UserFollowUp.is_converted.is_(False),
                UserFollowUp.next_send_at.isnot(None),
                UserFollowUp.next_send_at <= now,
            ).limit(50)
        )
        pending = list(rows)

        for fu in pending:
            try:
                await _process_one(db, bot, fu)
                sent_count += 1
            except Exception:
                logger.exception("Error processing follow-up for user_id=%d", fu.user_id)

        await db.commit()

    return sent_count


async def _process_one(db: AsyncSession, bot: Bot, fu: UserFollowUp) -> None:
    """Отправить следующее сообщение пользователю и обновить состояние."""
    next_step = _get_next_step(fu.current_step)

    msg = await db.scalar(
        select(FollowUpMessage).where(
            FollowUpMessage.step == next_step,
            FollowUpMessage.active.is_(True),
        )
    )
    if msg is None:
        # Нет активного сообщения для шага — пропускаем.
        fu.next_send_at = None
        fu.updated_at = datetime.utcnow()
        return

    user = await db.scalar(select(User).where(User.id == fu.user_id))
    if user is None or user.telegram_id is None:
        fu.next_send_at = None
        fu.updated_at = datetime.utcnow()
        return

    telegram_id = user.telegram_id

    try:
        await _send_followup_message(bot, telegram_id, msg)
    except Exception as e:
        err_str = str(e).lower()
        if "blocked" in err_str or "deactivated" in err_str or "chat not found" in err_str:
            fu.is_converted = True
            fu.next_send_at = None
            fu.updated_at = datetime.utcnow()
            logger.info("Follow-up stopped for user_id=%d (blocked/deactivated)", fu.user_id)
            return
        raise

    fu.current_step = next_step
    fu.updated_at = datetime.utcnow()

    # Определить следующее время отправки.
    if next_step == 1:
        # После msg1 → msg2.
        msg2 = await db.scalar(
            select(FollowUpMessage).where(FollowUpMessage.step == 2, FollowUpMessage.active.is_(True))
        )
        delay = msg2.delay_minutes if msg2 else 600
        fu.next_send_at = datetime.utcnow() + timedelta(minutes=delay)
    elif next_step == 2:
        # После msg2 → msg3.
        msg3 = await db.scalar(
            select(FollowUpMessage).where(FollowUpMessage.step == 3, FollowUpMessage.active.is_(True))
        )
        delay = msg3.delay_minutes if msg3 else 1440
        fu.next_send_at = datetime.utcnow() + timedelta(minutes=delay)
    elif next_step == 3:
        # После msg3 → msg2 (цикл).
        fu.cycle_count += 1
        msg2 = await db.scalar(
            select(FollowUpMessage).where(FollowUpMessage.step == 2, FollowUpMessage.active.is_(True))
        )
        delay = msg2.delay_minutes if msg2 else 600
        fu.next_send_at = datetime.utcnow() + timedelta(minutes=delay)
    else:
        fu.next_send_at = None

    logger.info(
        "Follow-up step %d sent to user_id=%d (tg=%d), next at %s",
        next_step, fu.user_id, telegram_id, fu.next_send_at,
    )


def _get_next_step(current_step: int) -> int:
    """Определить следующий шаг: 0→1, 1→2, 2→3, 3→2 (цикл)."""
    if current_step == 0:
        return 1
    if current_step == 1:
        return 2
    if current_step == 2:
        return 3
    # current_step == 3 → цикл обратно к 2.
    return 2


async def _send_followup_message(bot: Bot, chat_id: int, msg: FollowUpMessage) -> None:
    """Отправить конкретное follow-up сообщение пользователю."""
    keyboard = None
    if msg.button_text and msg.button_url:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=msg.button_text, url=msg.button_url)]
            ]
        )

    photo_paths = msg.photo_paths or []
    resolved_photos = [_resolve_path(p) for p in photo_paths if p]
    existing_photos = [p for p in resolved_photos if p.is_file()]

    if msg.is_album and len(existing_photos) > 1:
        # Отправить альбом фотографий.
        media = [
            InputMediaPhoto(media=FSInputFile(str(p)))
            for p in existing_photos
        ]
        await bot.send_media_group(chat_id=chat_id, media=media)
        # Текст + кнопка отдельным сообщением после альбома.
        if msg.text:
            await bot.send_message(
                chat_id=chat_id,
                text=msg.text,
                parse_mode=msg.parse_mode or "HTML",
                reply_markup=keyboard,
            )
    elif existing_photos:
        # Фото отдельно, затем текст + кнопка отдельным сообщением.
        await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(str(existing_photos[0])),
        )
        if msg.text:
            await bot.send_message(
                chat_id=chat_id,
                text=msg.text,
                parse_mode=msg.parse_mode or "HTML",
                reply_markup=keyboard,
            )
    else:
        # Только текст.
        if msg.text:
            await bot.send_message(
                chat_id=chat_id,
                text=msg.text,
                parse_mode=msg.parse_mode or "HTML",
                reply_markup=keyboard,
            )


def _resolve_path(path_str: str) -> Path:
    """Резолвить путь к файлу относительно корня проекта."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return BASE_DIR / p
