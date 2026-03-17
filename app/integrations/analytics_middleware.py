"""Aiogram middleware that auto-tracks every user interaction."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.analytics import EventCategory
from app.models.entities import User
from app.services.analytics.tracker import track_event

logger = logging.getLogger(__name__)


async def _resolve_user_id(telegram_id: int) -> int | None:
    async with SessionLocal() as db:
        user = await db.scalar(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        return user


class AnalyticsMiddleware(BaseMiddleware):
    """Intercepts every update to record analytics events."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            await self._track(event)
        except Exception:
            logger.exception("Analytics tracking failed")

        return await handler(event, data)

    async def _track(self, event: TelegramObject) -> None:
        if isinstance(event, Message):
            await self._track_message(event)
        elif isinstance(event, CallbackQuery):
            await self._track_callback(event)

    async def _track_message(self, msg: Message) -> None:
        tg_user = msg.from_user
        if not tg_user:
            return

        user_id = await _resolve_user_id(tg_user.id)

        if msg.text and msg.text.startswith("/"):
            event_type = "command"
            category = EventCategory.lifecycle if msg.text == "/start" else EventCategory.action
            event_data = {"command": msg.text.split()[0]}

            if msg.text == "/start":
                event_type = "bot_start"
                event_data["source"] = "command"
        else:
            event_type = "message_sent"
            category = EventCategory.message
            event_data = {
                "content_type": msg.content_type.value if msg.content_type else "unknown",
                "text_length": len(msg.text) if msg.text else 0,
            }

        await track_event(
            event_type=event_type,
            category=category,
            user_id=user_id,
            telegram_id=tg_user.id,
            data=event_data,
        )

    async def _track_callback(self, cb: CallbackQuery) -> None:
        tg_user = cb.from_user
        if not tg_user:
            return

        user_id = await _resolve_user_id(tg_user.id)
        data_str = cb.data or ""

        if data_str == "nav_home":
            event_type = "nav_home"
            category = EventCategory.navigation
            event_data = {"action": "home"}
        elif data_str.startswith("menu_"):
            event_type = "menu_click"
            category = EventCategory.navigation
            menu_id = data_str.split("_", 1)[1] if "_" in data_str else data_str
            title = await _get_menu_title(menu_id)
            event_data = {"menu_item_id": menu_id, "menu_title": title}
        else:
            event_type = "callback_query"
            category = EventCategory.action
            event_data = {"callback_data": data_str}

        await track_event(
            event_type=event_type,
            category=category,
            user_id=user_id,
            telegram_id=tg_user.id,
            data=event_data,
        )


async def _get_menu_title(menu_id: str) -> str | None:
    try:
        item_id = int(menu_id)
    except (ValueError, TypeError):
        return None

    from app.models.entities import ContentMenuItem

    async with SessionLocal() as db:
        item = await db.get(ContentMenuItem, item_id)
        return item.title if item else None
