"""Aggregation queries for analytics dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, cast, func, select, Date, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import UserEvent, UserSession, UserStatus
from app.models.entities import User


async def overview(db: AsyncSession) -> dict:
    """High-level KPIs for the analytics dashboard."""
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_today = await db.scalar(
        select(func.count(func.distinct(UserEvent.user_id)))
        .where(UserEvent.created_at >= datetime.combine(today, datetime.min.time()))
    ) or 0
    active_week = await db.scalar(
        select(func.count(func.distinct(UserEvent.user_id)))
        .where(UserEvent.created_at >= week_ago)
    ) or 0
    active_month = await db.scalar(
        select(func.count(func.distinct(UserEvent.user_id)))
        .where(UserEvent.created_at >= month_ago)
    ) or 0
    total_events = await db.scalar(select(func.count(UserEvent.id))) or 0
    events_today = await db.scalar(
        select(func.count(UserEvent.id))
        .where(UserEvent.created_at >= datetime.combine(today, datetime.min.time()))
    ) or 0

    blocked = await db.scalar(
        select(func.count()).select_from(UserStatus).where(UserStatus.is_blocked.is_(True))
    ) or 0
    deleted = await db.scalar(
        select(func.count()).select_from(UserStatus).where(UserStatus.is_deleted.is_(True))
    ) or 0

    new_today = await db.scalar(
        select(func.count(User.id))
        .where(User.created_at >= datetime.combine(today, datetime.min.time()))
    ) or 0
    new_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    ) or 0

    return {
        "total_users": total_users,
        "active_today": active_today,
        "active_week": active_week,
        "active_month": active_month,
        "total_events": total_events,
        "events_today": events_today,
        "blocked_users": blocked,
        "deleted_accounts": deleted,
        "new_users_today": new_today,
        "new_users_week": new_week,
    }


async def activity_chart(db: AsyncSession, days: int = 30) -> list[dict]:
    """Daily active users + events count for the last *days* days."""
    since = datetime.utcnow() - timedelta(days=days)
    date_col = cast(UserEvent.created_at, Date)

    rows = (
        await db.execute(
            select(
                date_col.label("day"),
                func.count(func.distinct(UserEvent.user_id)).label("dau"),
                func.count(UserEvent.id).label("events"),
            )
            .where(UserEvent.created_at >= since)
            .group_by(date_col)
            .order_by(date_col)
        )
    ).all()

    return [
        {"date": str(r.day), "dau": r.dau, "events": r.events}
        for r in rows
    ]


async def menu_heatmap(db: AsyncSession, days: int = 30) -> list[dict]:
    """Top menu items by click count."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                UserEvent.event_data["menu_item_id"].as_string().label("item_id"),
                UserEvent.event_data["menu_title"].as_string().label("title"),
                func.count(UserEvent.id).label("clicks"),
                func.count(func.distinct(UserEvent.user_id)).label("unique_users"),
            )
            .where(
                UserEvent.event_type == "menu_click",
                UserEvent.created_at >= since,
            )
            .group_by("item_id", "title")
            .order_by(func.count(UserEvent.id).desc())
            .limit(50)
        )
    ).all()

    return [
        {
            "menu_item_id": r.item_id,
            "title": r.title,
            "clicks": r.clicks,
            "unique_users": r.unique_users,
        }
        for r in rows
    ]


async def event_breakdown(db: AsyncSession, days: int = 7) -> list[dict]:
    """Event counts grouped by event_type."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                UserEvent.event_type,
                UserEvent.event_category,
                func.count(UserEvent.id).label("cnt"),
            )
            .where(UserEvent.created_at >= since)
            .group_by(UserEvent.event_type, UserEvent.event_category)
            .order_by(func.count(UserEvent.id).desc())
        )
    ).all()

    return [
        {"event_type": r.event_type, "category": r.event_category, "count": r.cnt}
        for r in rows
    ]


async def user_activity_detail(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    sort_by: str = "last_active",
) -> dict:
    """Paginated user list with activity metrics."""
    stmt = (
        select(
            User.id,
            User.telegram_id,
            User.first_name,
            User.username,
            User.created_at,
            UserStatus.is_blocked,
            UserStatus.is_deleted,
            UserStatus.is_active,
            UserStatus.last_active_at,
            UserStatus.total_events,
            UserStatus.total_sessions,
            UserStatus.blocked_at,
            UserStatus.deleted_at,
        )
        .outerjoin(UserStatus, User.id == UserStatus.user_id)
    )

    if status_filter == "blocked":
        stmt = stmt.where(UserStatus.is_blocked.is_(True))
    elif status_filter == "deleted":
        stmt = stmt.where(UserStatus.is_deleted.is_(True))
    elif status_filter == "active":
        stmt = stmt.where(
            (UserStatus.is_active.is_(True)) | (UserStatus.user_id.is_(None))
        )
    elif status_filter == "inactive":
        stmt = stmt.where(UserStatus.is_active.is_(False))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    order_col = {
        "last_active": UserStatus.last_active_at,
        "total_events": UserStatus.total_events,
        "created": User.created_at,
    }.get(sort_by, UserStatus.last_active_at)

    stmt = stmt.order_by(order_col.desc().nullslast()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).all()

    items = [
        {
            "id": r.id,
            "telegram_id": r.telegram_id,
            "first_name": r.first_name,
            "username": r.username,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "is_blocked": bool(r.is_blocked),
            "is_deleted": bool(r.is_deleted),
            "is_active": bool(r.is_active) if r.is_active is not None else True,
            "last_active_at": r.last_active_at.isoformat() if r.last_active_at else None,
            "total_events": r.total_events or 0,
            "total_sessions": r.total_sessions or 0,
            "blocked_at": r.blocked_at.isoformat() if r.blocked_at else None,
            "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
        }
        for r in rows
    ]

    return {"items": items, "total": total}


async def user_event_feed(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Recent events for a specific user."""
    rows = (
        await db.execute(
            select(UserEvent)
            .where(UserEvent.user_id == user_id)
            .order_by(UserEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_category": e.event_category,
            "event_data": e.event_data,
            "session_id": e.session_id,
            "created_at": e.created_at.isoformat(),
        }
        for e in rows
    ]


async def new_users_chart(db: AsyncSession, days: int = 30) -> list[dict]:
    """Daily new user registrations."""
    since = datetime.utcnow() - timedelta(days=days)
    date_col = cast(User.created_at, Date)

    rows = (
        await db.execute(
            select(
                date_col.label("day"),
                func.count(User.id).label("count"),
            )
            .where(User.created_at >= since)
            .group_by(date_col)
            .order_by(date_col)
        )
    ).all()

    return [{"date": str(r.day), "count": r.count} for r in rows]


async def session_stats(db: AsyncSession, days: int = 7) -> dict:
    """Session duration and count metrics."""
    since = datetime.utcnow() - timedelta(days=days)

    total = await db.scalar(
        select(func.count(UserSession.id)).where(UserSession.started_at >= since)
    ) or 0

    avg_events = await db.scalar(
        select(func.avg(UserSession.events_count)).where(UserSession.started_at >= since)
    ) or 0

    return {
        "total_sessions": total,
        "avg_events_per_session": round(float(avg_events), 1),
    }


async def retention_data(db: AsyncSession, weeks: int = 8) -> list[dict]:
    """Weekly cohort retention: % of users returning in week N."""
    now = datetime.utcnow()
    results = []

    for w in range(weeks):
        cohort_start = now - timedelta(weeks=w + 1)
        cohort_end = now - timedelta(weeks=w)

        cohort_size = await db.scalar(
            select(func.count(User.id)).where(
                User.created_at >= cohort_start, User.created_at < cohort_end,
            )
        ) or 0

        if cohort_size == 0:
            results.append({
                "week": w, "cohort_start": str(cohort_start.date()),
                "cohort_size": 0, "returned": 0, "rate": 0,
            })
            continue

        returned = await db.scalar(
            select(func.count(func.distinct(UserEvent.user_id))).where(
                UserEvent.user_id.in_(
                    select(User.id).where(
                        User.created_at >= cohort_start, User.created_at < cohort_end,
                    )
                ),
                UserEvent.created_at >= cohort_end,
            )
        ) or 0

        results.append({
            "week": w,
            "cohort_start": str(cohort_start.date()),
            "cohort_size": cohort_size,
            "returned": returned,
            "rate": round(returned / cohort_size * 100, 1),
        })

    return results
