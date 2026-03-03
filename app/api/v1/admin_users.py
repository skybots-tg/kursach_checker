from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, CreditsBalance, User

router = APIRouter()


class UserUpdateIn(BaseModel):
    first_name: str | None = None
    username: str | None = None


class CreditsUpdateIn(BaseModel):
    credits_available: int


@router.get("")
async def list_users(
    q: str | None = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    stmt = select(User).order_by(User.id.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.username.ilike(like)) | (User.first_name.ilike(like)))

    users = await db.scalars(stmt)
    result = []
    for u in users:
        credits = await db.get(CreditsBalance, u.id)
        result.append(
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "first_name": u.first_name,
                "username": u.username,
                "credits_available": credits.credits_available if credits else 0,
                "created_at": u.created_at,
            }
        )
    return result


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    credits = await db.get(CreditsBalance, user.id)
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "username": user.username,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "credits_available": credits.credits_available if credits else 0,
    }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdateIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.username is not None:
        user.username = payload.username
    await db.commit()
    return {"ok": True}


@router.put("/{user_id}/credits")
async def update_user_credits(
    user_id: int,
    payload: CreditsUpdateIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    credits = await db.get(CreditsBalance, user_id)
    if not credits:
        credits = CreditsBalance(user_id=user_id, credits_available=payload.credits_available)
        db.add(credits)
    else:
        credits.credits_available = payload.credits_available
    await db.commit()
    return {"ok": True}

