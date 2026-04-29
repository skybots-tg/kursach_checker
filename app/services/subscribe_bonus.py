"""Бонус за подписку на канал.

Логика:
* В env задаются ``subscribe_bonus_channel_username`` (без @) и
  ``subscribe_bonus_amount``. Если username пуст — фича выключена.
* Бот должен быть добавлен в канал администратором, иначе
  ``getChatMember`` вернёт ошибку.
* Бонус выдаётся ОДИН раз навсегда: дедупликация — по записям в
  ``credits_transactions`` с ``reference_type='channel_subscription'``.
* При повторном нажатии «проверить» отвечаем, что бонус уже получен.
* Если пользователь не подписан — никакого начисления, просим подписаться.
"""

from __future__ import annotations

import enum
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import CreditsTransaction, CreditsTransactionType
from app.services.credits import add_credits

logger = logging.getLogger(__name__)


SUBSCRIBE_REFERENCE_TYPE = "channel_subscription"

# Статусы getChatMember, при которых считаем человека подписанным.
SUBSCRIBED_STATUSES: frozenset[str] = frozenset(
    {"member", "administrator", "creator", "restricted"}
)


class SubscribeOutcome(enum.Enum):
    """Результат попытки выдать бонус за подписку на канал."""

    granted = "granted"            # начислили сейчас
    already_received = "already"   # ранее уже получал
    not_subscribed = "not_sub"     # подписки нет
    disabled = "disabled"          # фича не настроена в env
    error = "error"                # API-ошибка / бот не админ


def is_enabled() -> bool:
    """Включена ли фича бонуса за подписку (есть ли username канала)."""
    return bool((settings.subscribe_bonus_channel_username or "").strip())


def channel_username() -> str:
    """Username канала без ведущего ``@`` (для построения ссылок)."""
    return (settings.subscribe_bonus_channel_username or "").strip().lstrip("@")


def channel_link() -> str:
    """Публичная ссылка на канал вида ``https://t.me/<username>``."""
    return f"https://t.me/{channel_username()}"


def channel_chat_id() -> str:
    """Идентификатор чата для Bot API (``@username``)."""
    return f"@{channel_username()}"


def bonus_amount() -> int:
    """Сколько кредитов начисляется за подтверждённую подписку."""
    value = int(settings.subscribe_bonus_amount or 0)
    return max(0, value)


async def has_received_subscribe_bonus(
    db: AsyncSession, user_id: int,
) -> bool:
    """True, если по этому user_id уже было начисление за подписку."""
    row = await db.scalar(
        select(CreditsTransaction.id).where(
            CreditsTransaction.user_id == user_id,
            CreditsTransaction.reference_type == SUBSCRIBE_REFERENCE_TYPE,
        ).limit(1)
    )
    return row is not None


async def is_subscribed_to_channel(
    bot: Bot, telegram_user_id: int,
) -> bool | None:
    """Проверить подписку пользователя на настроенный канал.

    Возвращает:
    * ``True`` — пользователь подписан;
    * ``False`` — точно не подписан (статус left/kicked);
    * ``None`` — фича выключена или Telegram вернул ошибку (бот не
      админ канала, канал не существует, временный сбой).
    """
    if not is_enabled():
        return None

    try:
        member = await bot.get_chat_member(
            chat_id=channel_chat_id(),
            user_id=telegram_user_id,
        )
    except TelegramAPIError:
        logger.exception(
            "Failed to call getChatMember for channel=%s user=%s",
            channel_chat_id(), telegram_user_id,
        )
        return None

    status = getattr(member, "status", None)
    if status in SUBSCRIBED_STATUSES:
        return True
    if status in {"left", "kicked"}:
        return False
    return None


async def try_grant_subscribe_bonus(
    db: AsyncSession, bot: Bot, *, user_id: int, telegram_user_id: int,
) -> SubscribeOutcome:
    """Проверить подписку и при первом успехе начислить бонус.

    Не коммитит сессию — это ответственность вызывающего кода.
    """
    if not is_enabled() or bonus_amount() <= 0:
        return SubscribeOutcome.disabled

    if await has_received_subscribe_bonus(db, user_id):
        return SubscribeOutcome.already_received

    subscribed = await is_subscribed_to_channel(bot, telegram_user_id)
    if subscribed is None:
        return SubscribeOutcome.error
    if subscribed is False:
        return SubscribeOutcome.not_subscribed

    await add_credits(
        db,
        user_id=user_id,
        amount=bonus_amount(),
        tx_type=CreditsTransactionType.topup,
        description=(
            f"Subscribe bonus for @{channel_username()}: +{bonus_amount()}"
        ),
        reference_type=SUBSCRIBE_REFERENCE_TYPE,
        reference_id=None,
    )
    return SubscribeOutcome.granted
