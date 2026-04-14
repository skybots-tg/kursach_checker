"""Broadcast audience segmentation — query building and counting."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import UserStatus
from app.models.entities import Order, OrderStatus, User


SEGMENT_LABELS = {
    "all": "Все пользователи",
    "paid": "Оплачивали",
    "viewers": "Только смотрели",
    "unpaid_invoice": "Создали счёт, но не оплатили",
    "recent": "Зарегистрировались недавно",
}


def build_segment_query(segment: dict) -> Select:
    """Return a SELECT(User.id, User.telegram_id) filtered by segment."""
    stmt = select(User.id, User.telegram_id)

    seg_type = segment.get("type", "all")
    date_from = _parse_date(segment.get("date_from"))
    date_to = _parse_date(segment.get("date_to"))

    if seg_type == "paid":
        paid_subq = (
            select(Order.user_id)
            .where(Order.status == OrderStatus.paid)
            .correlate(None)
        )
        stmt = stmt.where(User.id.in_(paid_subq))

    elif seg_type == "viewers":
        paid_subq = (
            select(Order.user_id)
            .where(Order.status == OrderStatus.paid)
            .correlate(None)
        )
        stmt = stmt.where(~User.id.in_(paid_subq))

    elif seg_type == "unpaid_invoice":
        created_subq = select(Order.user_id).where(
            Order.status == OrderStatus.created,
        )
        if date_from:
            created_subq = created_subq.where(Order.created_at >= date_from)
        if date_to:
            created_subq = created_subq.where(Order.created_at <= date_to)
        created_subq = created_subq.correlate(None)

        paid_subq = (
            select(Order.user_id)
            .where(Order.status == OrderStatus.paid)
            .correlate(None)
        )
        stmt = stmt.where(User.id.in_(created_subq), ~User.id.in_(paid_subq))

    elif seg_type == "recent":
        if date_from:
            stmt = stmt.where(User.created_at >= date_from)
        if date_to:
            stmt = stmt.where(User.created_at <= date_to)

    return stmt


async def count_audience(db: AsyncSession, segment: dict) -> dict:
    """Count total and active (non-blocked) users for given segment."""
    base = build_segment_query(segment).subquery()

    total = await db.scalar(
        select(func.count()).select_from(base)
    ) or 0

    active = await db.scalar(
        select(func.count())
        .select_from(base)
        .outerjoin(UserStatus, base.c.id == UserStatus.user_id)
        .where(
            (UserStatus.is_blocked.is_(False)) | (UserStatus.is_blocked.is_(None))
        )
    ) or 0

    return {"total": total, "active": active}


async def get_segment_user_ids(
    db: AsyncSession, segment: dict,
) -> list[tuple[int, int]]:
    """Return list of (user_id, telegram_id) matching the segment, excluding blocked."""
    base = build_segment_query(segment)
    stmt = (
        base
        .outerjoin(UserStatus, User.id == UserStatus.user_id)
        .where(
            (UserStatus.is_blocked.is_(False)) | (UserStatus.is_blocked.is_(None))
        )
    )
    rows = await db.execute(stmt)
    return [(r.id, r.telegram_id) for r in rows]


def _parse_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None
