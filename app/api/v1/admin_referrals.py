"""Admin API для реферальной программы."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import (
    AdminUser,
    CreditsTransactionType,
    Referral,
    User,
)
from app.services.credits import add_credits
from app.services.referrals import REFERRAL_BONUS_AMOUNT

router = APIRouter()


class ReferralGrantIn(BaseModel):
    bonus_amount: int | None = None


def _user_dict(user: User | None) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "username": user.username,
    }


@router.get("")
async def list_referrals(
    status: str | None = None,
    q: str | None = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Список рефералов с данными по инвайтеру и приглашённому.

    *status*: ``pending`` | ``granted`` — фильтр по выдаче бонуса.
    *q*: поиск по username / first_name инвайтера или приглашённого.
    """
    _ = current_admin

    inviter = aliased(User)
    invited = aliased(User)

    stmt = (
        select(Referral, inviter, invited)
        .join(inviter, inviter.id == Referral.inviter_user_id)
        .join(invited, invited.id == Referral.invited_user_id)
        .order_by(Referral.id.desc())
    )

    if status == "pending":
        stmt = stmt.where(Referral.bonus_granted_at.is_(None))
    elif status == "granted":
        stmt = stmt.where(Referral.bonus_granted_at.is_not(None))

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            inviter.username.ilike(like)
            | inviter.first_name.ilike(like)
            | invited.username.ilike(like)
            | invited.first_name.ilike(like)
        )

    rows = await db.execute(stmt)
    result: list[dict] = []
    for ref, inv_user, invd_user in rows:
        result.append(
            {
                "id": ref.id,
                "inviter": _user_dict(inv_user),
                "invited": _user_dict(invd_user),
                "created_at": ref.created_at,
                "bonus_granted_at": ref.bonus_granted_at,
                "bonus_amount": ref.bonus_amount,
                "status": "granted" if ref.bonus_granted_at else "pending",
            }
        )
    return result


@router.get("/stats")
async def referrals_stats(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Агрегированная статистика по рефералам для верхних карточек."""
    _ = current_admin

    total = await db.scalar(select(func.count(Referral.id))) or 0
    granted = await db.scalar(
        select(func.count(Referral.id)).where(
            Referral.bonus_granted_at.is_not(None)
        )
    ) or 0
    pending = total - granted
    bonuses_total = await db.scalar(
        select(func.coalesce(func.sum(Referral.bonus_amount), 0))
    ) or 0

    top_inviters_rows = await db.execute(
        select(
            User.id,
            User.telegram_id,
            User.first_name,
            User.username,
            func.count(Referral.id).label("invited_count"),
            func.coalesce(func.sum(Referral.bonus_amount), 0).label(
                "bonus_total"
            ),
        )
        .join(Referral, Referral.inviter_user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(Referral.id).desc())
        .limit(10)
    )

    top_inviters = [
        {
            "user": {
                "id": uid,
                "telegram_id": tg_id,
                "first_name": first_name,
                "username": username,
            },
            "invited_count": int(invited_count),
            "bonus_total": int(bonus_total),
        }
        for uid, tg_id, first_name, username, invited_count, bonus_total
        in top_inviters_rows
    ]

    return {
        "total": int(total),
        "granted": int(granted),
        "pending": int(pending),
        "bonuses_total": int(bonuses_total),
        "bonus_per_referral": REFERRAL_BONUS_AMOUNT,
        "top_inviters": top_inviters,
    }


@router.post("/{referral_id}/grant")
async def grant_bonus_manually(
    referral_id: int,
    payload: ReferralGrantIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Выдать бонус вручную (если алгоритм не сработал или нужна компенсация)."""
    ref = await db.get(Referral, referral_id)
    if ref is None:
        raise HTTPException(status_code=404, detail="Реферал не найден")
    if ref.bonus_granted_at is not None:
        raise HTTPException(status_code=400, detail="Бонус уже был начислен")

    amount = payload.bonus_amount or REFERRAL_BONUS_AMOUNT
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount должен быть > 0")

    await add_credits(
        db,
        user_id=ref.inviter_user_id,
        amount=amount,
        tx_type=CreditsTransactionType.topup,
        description=(
            f"Referral bonus (manual by admin #{current_admin.id}) "
            f"for invited user #{ref.invited_user_id}"
        ),
        reference_type="referral",
        reference_id=ref.id,
    )
    ref.bonus_granted_at = datetime.utcnow()
    ref.bonus_amount = amount
    await db.commit()
    return {"ok": True, "bonus_amount": amount}


@router.delete("/{referral_id}")
async def delete_referral(
    referral_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Удалить запись о реферале (например, при фроде). Бонус не откатывает."""
    _ = current_admin
    ref = await db.get(Referral, referral_id)
    if ref is None:
        raise HTTPException(status_code=404, detail="Реферал не найден")
    await db.delete(ref)
    await db.commit()
    return {"ok": True}
