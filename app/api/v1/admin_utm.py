"""Admin UTM tracking links — create tags, view stats."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.core.config import settings
from app.db.session import get_db
from app.models import AdminUser, User
from app.models.analytics import UserEvent

router = APIRouter()


def _parse_date_range(
    days: int | None, date_from: str | None, date_to: str | None,
) -> tuple[datetime | None, datetime | None]:
    """Resolve query params into (since, until) datetime bounds."""
    since = None
    until = None
    if date_from:
        try:
            since = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            until = datetime.fromisoformat(date_to + "T23:59:59") if "T" not in date_to else datetime.fromisoformat(date_to)
        except ValueError:
            pass
    if since is None and days and days < 9999:
        since = datetime.utcnow() - timedelta(days=days)
    return since, until


@router.get("/stats")
async def utm_stats(
    days: int = Query(30, ge=1, le=9999),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregate UTM stats: users per tag, daily breakdown."""
    _ = current_admin
    since, until = _parse_date_range(days, date_from, date_to)

    q = (
        select(
            User.utm_source,
            func.count(User.id).label("total_users"),
            func.min(User.created_at).label("first_seen"),
            func.max(User.created_at).label("last_seen"),
        )
        .where(User.utm_source.isnot(None))
    )
    if since:
        q = q.where(User.created_at >= since)
    if until:
        q = q.where(User.created_at <= until)
    by_source = (await db.execute(
        q.group_by(User.utm_source).order_by(func.count(User.id).desc())
    )).all()

    total_utm = sum(r.total_users for r in by_source)
    oq = select(func.count(User.id)).where(User.utm_source.is_(None))
    if since:
        oq = oq.where(User.created_at >= since)
    if until:
        oq = oq.where(User.created_at <= until)
    total_organic = await db.scalar(oq) or 0

    sources = [
        {
            "utm_source": r.utm_source,
            "total_users": r.total_users,
            "first_seen": r.first_seen.isoformat() if r.first_seen else None,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
        }
        for r in by_source
    ]

    return {
        "total_utm_users": total_utm,
        "total_organic_users": total_organic,
        "sources": sources,
    }


@router.get("/daily")
async def utm_daily(
    days: int = Query(30, ge=1, le=9999),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Daily new users grouped by UTM source (for chart)."""
    _ = current_admin
    since, until = _parse_date_range(days, date_from, date_to)
    date_col = cast(User.created_at, Date)

    q = (
        select(
            date_col.label("day"),
            func.coalesce(User.utm_source, "__organic__").label("source"),
            func.count(User.id).label("count"),
        )
    )
    if since:
        q = q.where(User.created_at >= since)
    if until:
        q = q.where(User.created_at <= until)
    rows = (await db.execute(q.group_by(date_col, "source").order_by(date_col))).all()

    return [
        {"date": str(r.day), "source": r.source, "count": r.count}
        for r in rows
    ]


@router.get("/users")
async def utm_users(
    source: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List users that came from a specific UTM source."""
    _ = current_admin
    base = select(User).where(User.utm_source == source)

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            base = base.where(User.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to + "T23:59:59") if "T" not in date_to else datetime.fromisoformat(date_to)
            base = base.where(User.created_at <= dt_to)
        except ValueError:
            pass

    total = await db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    rows = (
        await db.execute(
            base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "first_name": u.first_name,
                "username": u.username,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ],
    }


@router.get("/generate")
async def utm_generate_link(
    tag: str = Query(..., min_length=1, max_length=128),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """Generate a bot deep link for a given UTM tag."""
    _ = current_admin
    username = (settings.telegram_bot_username or "").lstrip("@")
    if not username:
        return {"link": f"https://t.me/BOT?start={tag}", "warning": "bot username not configured"}
    return {"link": f"https://t.me/{username}?start={tag}"}
