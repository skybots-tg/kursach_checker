"""Admin API for follow-up (дожимы) messages — CRUD + stats."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, FollowUpMessage, UserFollowUp

router = APIRouter()


class FollowUpMessageOut(BaseModel):
    id: int
    step: int
    delay_minutes: int
    text: str
    parse_mode: str
    button_text: str | None
    button_url: str | None
    photo_paths: list
    is_album: bool
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FollowUpMessageUpdate(BaseModel):
    delay_minutes: int | None = None
    text: str | None = None
    parse_mode: str | None = None
    button_text: str | None = None
    button_url: str | None = None
    photo_paths: list | None = None
    is_album: bool | None = None
    active: bool | None = None


class FollowUpStatsOut(BaseModel):
    total_users: int
    active_chains: int
    converted: int
    step_1_sent: int
    step_2_sent: int
    step_3_sent: int


@router.get("/followups", summary="Список follow-up сообщений")
async def list_followups(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[FollowUpMessageOut]:
    rows = await db.scalars(
        select(FollowUpMessage).order_by(FollowUpMessage.step.asc())
    )
    return [FollowUpMessageOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/followups/stats", summary="Статистика дожимов")
async def followup_stats(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> FollowUpStatsOut:
    total = await db.scalar(select(func.count(UserFollowUp.id))) or 0
    active = await db.scalar(
        select(func.count(UserFollowUp.id)).where(
            UserFollowUp.is_converted.is_(False),
            UserFollowUp.next_send_at.isnot(None),
        )
    ) or 0
    converted = await db.scalar(
        select(func.count(UserFollowUp.id)).where(UserFollowUp.is_converted.is_(True))
    ) or 0
    step1 = await db.scalar(
        select(func.count(UserFollowUp.id)).where(UserFollowUp.current_step >= 1)
    ) or 0
    step2 = await db.scalar(
        select(func.count(UserFollowUp.id)).where(UserFollowUp.current_step >= 2)
    ) or 0
    step3 = await db.scalar(
        select(func.count(UserFollowUp.id)).where(UserFollowUp.current_step >= 3)
    ) or 0
    return FollowUpStatsOut(
        total_users=total,
        active_chains=active,
        converted=converted,
        step_1_sent=step1,
        step_2_sent=step2,
        step_3_sent=step3,
    )


@router.put("/followups/{step}", summary="Обновить follow-up сообщение")
async def update_followup(
    step: int,
    body: FollowUpMessageUpdate,
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> FollowUpMessageOut:
    msg = await db.scalar(
        select(FollowUpMessage).where(FollowUpMessage.step == step)
    )
    if msg is None:
        from fastapi import HTTPException
        raise HTTPException(404, f"Follow-up step {step} not found")

    updates = body.model_dump(exclude_unset=True)
    for key, val in updates.items():
        setattr(msg, key, val)
    msg.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(msg)
    return FollowUpMessageOut.model_validate(msg, from_attributes=True)
