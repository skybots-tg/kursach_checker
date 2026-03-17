"""Admin analytics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser
from app.services.analytics import aggregator

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    return await aggregator.overview(db)


@router.get("/activity-chart")
async def analytics_activity_chart(
    days: int = Query(30, ge=1, le=365),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    return await aggregator.activity_chart(db, days=days)


@router.get("/menu-heatmap")
async def analytics_menu_heatmap(
    days: int = Query(30, ge=1, le=365),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    return await aggregator.menu_heatmap(db, days=days)


@router.get("/event-breakdown")
async def analytics_event_breakdown(
    days: int = Query(7, ge=1, le=365),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    return await aggregator.event_breakdown(db, days=days)


@router.get("/users")
async def analytics_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    sort: str = Query("last_active"),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    return await aggregator.user_activity_detail(
        db, limit=limit, offset=offset, status_filter=status, sort_by=sort,
    )


@router.get("/users/{user_id}/events")
async def analytics_user_events(
    user_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    return await aggregator.user_event_feed(db, user_id, limit=limit, offset=offset)


@router.get("/new-users-chart")
async def analytics_new_users_chart(
    days: int = Query(30, ge=1, le=365),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    return await aggregator.new_users_chart(db, days=days)


@router.get("/sessions")
async def analytics_sessions(
    days: int = Query(7, ge=1, le=365),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    return await aggregator.session_stats(db, days=days)


@router.get("/retention")
async def analytics_retention(
    weeks: int = Query(8, ge=1, le=52),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    return await aggregator.retention_data(db, weeks=weeks)
