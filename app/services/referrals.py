"""Referral program service.

Правила:
* Один инвайтер на приглашённого (UNIQUE invited_user_id).
* Привязка реферала делается ОДИН раз при первом /start нового
  пользователя, если в параметре пришёл валидный ref_<inviter_id>.
* Бонус начисляется СРАЗУ после привязки (т.е. когда друг впервые зашёл
  в бота по реф-ссылке), без требования выполнять проверку.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import CreditsTransactionType, Referral, User
from app.services.credits import add_credits

logger = logging.getLogger(__name__)

REF_PAYLOAD_PREFIX = "ref_"

# Сколько кредитов начисляется инвайтеру за одного приглашённого.
# Число вынесено как константа, чтобы при необходимости быстро поменять.
REFERRAL_BONUS_AMOUNT = 1


def parse_ref_payload(start_arg: str | None) -> int | None:
    """Вернуть inviter_user_id из параметра /start ref_<id> или None."""
    if not start_arg:
        return None
    arg = start_arg.strip()
    if not arg.startswith(REF_PAYLOAD_PREFIX):
        return None
    raw = arg[len(REF_PAYLOAD_PREFIX):]
    if not raw.isdigit():
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def build_ref_link(inviter_user_id: int, bot_username: str | None = None) -> str:
    """Собрать персональную реф-ссылку для пользователя."""
    username = (bot_username or settings.telegram_bot_username or "").lstrip("@")
    if not username:
        # fallback на случай, если username бота не сконфигурирован
        return f"https://t.me/share?start={REF_PAYLOAD_PREFIX}{inviter_user_id}"
    return f"https://t.me/{username}?start={REF_PAYLOAD_PREFIX}{inviter_user_id}"


async def link_referral(
    db: AsyncSession,
    *,
    inviter_user_id: int,
    invited_user_id: int,
) -> Referral | None:
    """Создать связь инвайтер → приглашённый, если это допустимо.

    Возвращает созданную запись или None, если привязка не состоялась
    (самого себя, инвайтер не существует, уже была запись и т.п.).
    """
    if inviter_user_id == invited_user_id:
        return None

    inviter = await db.get(User, inviter_user_id)
    if inviter is None:
        return None

    existing = await db.scalar(
        select(Referral).where(Referral.invited_user_id == invited_user_id)
    )
    if existing is not None:
        return None

    ref = Referral(
        inviter_user_id=inviter_user_id,
        invited_user_id=invited_user_id,
    )
    db.add(ref)
    try:
        await db.flush()
    except IntegrityError:
        # гонка: кто-то уже записал — это ок, тихо выходим
        await db.rollback()
        return None
    return ref


async def get_referral_for_invited(
    db: AsyncSession, invited_user_id: int,
) -> Referral | None:
    return await db.scalar(
        select(Referral).where(Referral.invited_user_id == invited_user_id)
    )


async def try_grant_bonus_for_invited(
    db: AsyncSession,
    *,
    invited_user_id: int,
) -> Referral | None:
    """Начислить инвайтеру бонус, если у приглашённого он ещё не выдан.

    Возвращает Referral с выставленным bonus_granted_at, если бонус
    был начислён прямо сейчас, иначе None.
    """
    ref = await get_referral_for_invited(db, invited_user_id)
    if ref is None or ref.bonus_granted_at is not None:
        return None

    description = f"Referral bonus for invited user #{invited_user_id}"

    await add_credits(
        db,
        user_id=ref.inviter_user_id,
        amount=REFERRAL_BONUS_AMOUNT,
        tx_type=CreditsTransactionType.topup,
        description=description,
        reference_type="referral",
        reference_id=ref.id,
    )

    ref.bonus_granted_at = datetime.utcnow()
    ref.bonus_amount = REFERRAL_BONUS_AMOUNT
    return ref
