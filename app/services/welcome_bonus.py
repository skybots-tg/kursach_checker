"""Приветственный бонус новым пользователям.

При первом ``/start`` пользователю автоматически начисляется N
бесплатных проверок (задаётся параметром ``WELCOME_BONUS_AMOUNT``).

Источники значения, по приоритету:
    1) ``SystemSetting`` с ключом ``welcome_bonus`` (правится из админки);
    2) ``settings.welcome_bonus_amount`` из env (по умолчанию 3).

Если итоговое значение ``<= 0`` — приветственный бонус выключен.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import CreditsTransactionType, SystemSetting
from app.services.credits import add_credits

logger = logging.getLogger(__name__)


WELCOME_BONUS_KEY = "welcome_bonus"
WELCOME_REFERENCE_TYPE = "welcome_bonus"


async def get_welcome_bonus_amount(db: AsyncSession) -> int:
    """Получить актуальный размер приветственного бонуса (>=0)."""
    row = await db.get(SystemSetting, WELCOME_BONUS_KEY)
    if row is not None:
        try:
            value = int((row.value or {}).get(
                "amount", settings.welcome_bonus_amount,
            ))
        except (TypeError, ValueError):
            value = settings.welcome_bonus_amount
    else:
        value = settings.welcome_bonus_amount
    return max(0, value)


async def grant_welcome_bonus(
    db: AsyncSession, *, user_id: int,
) -> int:
    """Начислить приветственный бонус новому пользователю.

    Возвращает фактически начисленное количество кредитов
    (``0`` если бонус выключен или равен нулю).

    Сессию не коммитит — это ответственность вызывающего кода.
    """
    amount = await get_welcome_bonus_amount(db)
    if amount <= 0:
        return 0

    await add_credits(
        db,
        user_id=user_id,
        amount=amount,
        tx_type=CreditsTransactionType.topup,
        description=f"Welcome bonus for new user: +{amount}",
        reference_type=WELCOME_REFERENCE_TYPE,
        reference_id=None,
    )
    return amount
