"""Единая фабрика создания экземпляра ``aiogram.Bot``.

Все сценарии (поллинг, уведомления, рассылки) должны создавать бота
через :func:`make_bot`, чтобы дефолты (например, отключение
предпросмотра ссылок) применялись согласованно.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.core.config import settings


def make_bot() -> Bot:
    """Создать ``Bot`` с проектными дефолтами.

    Дефолты:
    * ``link_preview_is_disabled=True`` — отключаем предпросмотр URL во
      всех текстах, которые отправляет бот (приветствие, пункты меню,
      уведомления, рассылки). Это пожелание из админки: ссылки в
      сообщениях не должны разворачиваться в превью.
    """
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(link_preview_is_disabled=True),
    )
