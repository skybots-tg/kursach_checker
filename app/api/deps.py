from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import CreditsBalance, User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    token = authorization.split(" ", 1)[1]
    user_id = decode_access_token(token)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


async def get_current_user_or_token(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None, alias="token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Supports both Bearer header and ?token= query param (for file downloads via <a href>)."""
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ", 1)[1]
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    user_id = decode_access_token(raw_token)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


async def get_user_credits(db: AsyncSession, user_id: int) -> int:
    credits = await db.scalar(
        select(CreditsBalance.credits_available).where(CreditsBalance.user_id == user_id)
    )
    return int(credits or 0)


