"""Fire-and-forget event recording with session management."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.analytics import EventCategory, UserEvent, UserSession, UserStatus

logger = logging.getLogger(__name__)

SESSION_TIMEOUT = timedelta(minutes=30)

_active_sessions: dict[int, str] = {}


def _new_session_id() -> str:
    return uuid.uuid4().hex[:16]


async def track_event(
    *,
    event_type: str,
    category: str = EventCategory.action,
    user_id: int | None = None,
    telegram_id: int | None = None,
    data: dict | None = None,
    db: AsyncSession | None = None,
) -> None:
    """Record a single user event. Opens its own session when *db* is None."""
    try:
        if db is not None:
            await _write_event(db, event_type, category, user_id, telegram_id, data)
        else:
            async with SessionLocal() as session:
                await _write_event(
                    session, event_type, category, user_id, telegram_id, data,
                )
                await session.commit()
    except Exception:
        logger.exception("Failed to track event %s", event_type)


async def _write_event(
    db: AsyncSession,
    event_type: str,
    category: str,
    user_id: int | None,
    telegram_id: int | None,
    data: dict | None,
) -> None:
    sid = await _resolve_session(db, user_id, telegram_id)

    event = UserEvent(
        user_id=user_id,
        telegram_id=telegram_id,
        event_type=event_type,
        event_category=category,
        event_data=data,
        session_id=sid,
    )
    db.add(event)

    if user_id:
        await _touch_user_status(db, user_id)

    if sid:
        await db.execute(
            update(UserSession)
            .where(UserSession.session_id == sid)
            .values(
                last_activity_at=datetime.utcnow(),
                events_count=UserSession.events_count + 1,
            )
        )


async def _resolve_session(
    db: AsyncSession,
    user_id: int | None,
    telegram_id: int | None,
) -> str | None:
    key = user_id or telegram_id
    if key is None:
        return None

    existing_sid = _active_sessions.get(key)
    if existing_sid:
        sess = await db.scalar(
            select(UserSession).where(UserSession.session_id == existing_sid)
        )
        if sess and (datetime.utcnow() - sess.last_activity_at) < SESSION_TIMEOUT:
            return existing_sid

    return await start_session(
        user_id=user_id, telegram_id=telegram_id, platform="telegram", db=db,
    )


async def start_session(
    *,
    user_id: int | None = None,
    telegram_id: int | None = None,
    platform: str = "telegram",
    db: AsyncSession | None = None,
) -> str:
    sid = _new_session_id()

    async def _create(s: AsyncSession) -> None:
        sess = UserSession(
            user_id=user_id,
            telegram_id=telegram_id,
            session_id=sid,
            platform=platform,
        )
        s.add(sess)
        if user_id:
            await s.execute(
                update(UserStatus)
                .where(UserStatus.user_id == user_id)
                .values(total_sessions=UserStatus.total_sessions + 1)
            )

    if db:
        await _create(db)
    else:
        async with SessionLocal() as s:
            await _create(s)
            await s.commit()

    key = user_id or telegram_id
    if key:
        _active_sessions[key] = sid
    return sid


async def end_session(session_id: str, db: AsyncSession | None = None) -> None:
    async def _close(s: AsyncSession) -> None:
        await s.execute(
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(ended_at=datetime.utcnow())
        )

    if db:
        await _close(db)
    else:
        async with SessionLocal() as s:
            await _close(s)
            await s.commit()

    _active_sessions.pop(session_id, None)


async def _touch_user_status(db: AsyncSession, user_id: int) -> None:
    status = await db.get(UserStatus, user_id)
    if status is None:
        status = UserStatus(
            user_id=user_id,
            first_seen_at=datetime.utcnow(),
            last_active_at=datetime.utcnow(),
            total_events=1,
        )
        db.add(status)
    else:
        status.last_active_at = datetime.utcnow()
        status.total_events = (status.total_events or 0) + 1
        if status.is_blocked:
            status.is_blocked = False
            status.unblocked_at = datetime.utcnow()


async def mark_blocked(user_id: int) -> None:
    async with SessionLocal() as db:
        status = await db.get(UserStatus, user_id)
        if status:
            status.is_blocked = True
            status.is_active = False
            status.blocked_at = datetime.utcnow()
        else:
            db.add(UserStatus(
                user_id=user_id,
                is_blocked=True,
                is_active=False,
                blocked_at=datetime.utcnow(),
            ))
        await db.commit()


async def mark_deleted(user_id: int) -> None:
    async with SessionLocal() as db:
        status = await db.get(UserStatus, user_id)
        if status:
            status.is_deleted = True
            status.is_active = False
            status.deleted_at = datetime.utcnow()
        else:
            db.add(UserStatus(
                user_id=user_id,
                is_deleted=True,
                is_active=False,
                deleted_at=datetime.utcnow(),
            ))
        await db.commit()
