from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import (
    AdminUser,
    Check,
    CheckWorkerLog,
    CreditsBalance,
    CreditsTransaction,
    File,
    Order,
    PaymentProdamus,
    Referral,
    User,
    UserEvent,
    UserSession,
    UserStatus,
)
from app.services.audit import log_admin_action
from app.services.credits import set_credits

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
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await set_credits(
        db,
        user_id=user_id,
        new_value=payload.credits_available,
        admin_user_id=current_admin.id,
    )
    await db.commit()
    return {"ok": True}


@router.get("/{user_id}/credits/history")
async def get_user_credits_history(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    stmt = (
        select(CreditsTransaction)
        .where(CreditsTransaction.user_id == user_id)
        .order_by(CreditsTransaction.id.desc())
        .offset(offset)
        .limit(min(limit, 200))
    )
    rows = await db.scalars(stmt)
    return [
        {
            "id": t.id,
            "tx_type": t.tx_type,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "description": t.description,
            "reference_type": t.reference_type,
            "reference_id": t.reference_id,
            "created_at": t.created_at,
        }
        for t in rows
    ]


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Полностью удалить пользователя и все связанные данные.

    Каскадно чистятся: рефералы, кредиты, транзакции, заказы, платежи,
    проверки, worker-логи, файлы и аналитика. Используется в первую
    очередь для тестов реф-программы и удаления тестовых аккаунтов.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    snapshot = {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
    }

    # 1. Реферальные записи (где он инвайтер ИЛИ приглашённый).
    await db.execute(
        delete(Referral).where(
            (Referral.inviter_user_id == user_id)
            | (Referral.invited_user_id == user_id)
        )
    )

    # 2. Платежи Prodamus → завязаны на orders.id, поэтому сначала их.
    user_order_ids = list(
        (await db.scalars(
            select(Order.id).where(Order.user_id == user_id)
        )).all()
    )
    if user_order_ids:
        await db.execute(
            delete(PaymentProdamus).where(
                PaymentProdamus.order_id.in_(user_order_ids)
            )
        )
    await db.execute(delete(Order).where(Order.user_id == user_id))

    # 3. Логи воркера завязаны на checks.id — сначала логи, потом checks.
    user_check_ids = list(
        (await db.scalars(
            select(Check.id).where(Check.user_id == user_id)
        )).all()
    )
    if user_check_ids:
        await db.execute(
            delete(CheckWorkerLog).where(
                CheckWorkerLog.check_id.in_(user_check_ids)
            )
        )
    await db.execute(delete(Check).where(Check.user_id == user_id))

    # 4. Файлы пользователя (после удаления checks, которые на них ссылались).
    await db.execute(delete(File).where(File.user_id == user_id))

    # 5. Кредиты и история операций.
    await db.execute(
        delete(CreditsTransaction).where(CreditsTransaction.user_id == user_id)
    )
    await db.execute(
        delete(CreditsBalance).where(CreditsBalance.user_id == user_id)
    )

    # 6. Аналитика по пользователю.
    await db.execute(delete(UserEvent).where(UserEvent.user_id == user_id))
    await db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    await db.execute(delete(UserStatus).where(UserStatus.user_id == user_id))

    # 7. Сама запись пользователя.
    await db.delete(user)

    await log_admin_action(
        db, current_admin.id, "delete", "user", str(user_id), snapshot,
    )
    await db.commit()
    return {"ok": True, "deleted": snapshot}

