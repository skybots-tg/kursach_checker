from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models_users import CreditsBalance, User


class UserService:
    """Работа с пользователями и балансом кредитов."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_telegram_user(
        self,
        telegram_id: int,
        first_name: str | None,
        username: str | None,
    ) -> User:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
            )
            self.session.add(user)
            await self.session.flush()

            balance = CreditsBalance(user_id=user.id, credits_available=0)
            self.session.add(balance)
        user.last_login_at = datetime.utcnow()
        await self.session.flush()
        return user

    async def get_credits_balance(self, user_id: int) -> int:
        stmt = select(CreditsBalance).where(CreditsBalance.user_id == user_id)
        result = await self.session.execute(stmt)
        balance = result.scalar_one_or_none()
        if balance is None:
            balance = CreditsBalance(user_id=user_id, credits_available=0)
            self.session.add(balance)
            await self.session.flush()
        return balance.credits_available

    async def consume_credit(self, user_id: int) -> bool:
        stmt = select(CreditsBalance).where(CreditsBalance.user_id == user_id).with_for_update()
        result = await self.session.execute(stmt)
        balance = result.scalar_one_or_none()
        if balance is None or balance.credits_available <= 0:
            return False
        balance.credits_available -= 1
        await self.session.flush()
        return True

    async def add_credits(self, user_id: int, amount: int) -> None:
        if amount <= 0:
            return
        stmt = select(CreditsBalance).where(CreditsBalance.user_id == user_id).with_for_update()
        result = await self.session.execute(stmt)
        balance = result.scalar_one_or_none()
        if balance is None:
            balance = CreditsBalance(user_id=user_id, credits_available=0)
            self.session.add(balance)
        balance.credits_available += amount
        await self.session.flush()






