from __future__ import annotations

"""
Простая интеграция с Telegram Bot API для нотификаций из backend/воркера.

Задачи:
- отправка сервисных сообщений студенту (подтверждение оплаты, готовность проверки);
- использовать telegram_id пользователя (из БД), без дополнительных состояний.
"""

from typing import Any

import httpx

from backend.config import get_settings


async def send_text_message(telegram_id: int, text: str, disable_web_page_preview: bool = True) -> None:
    """
    Отправляет простое текстовое сообщение пользователю по его telegram_id.

    Ошибки сети/Telegram намеренно проглатываются, чтобы не ломать основной поток
    (проверку или обработку webhook'а оплаты).
    """
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token or token == "CHANGE_ME_BOT_TOKEN":
        # Бот не сконфигурирован — тихо выходим.
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_web_page_preview,
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(url, json=payload)
        except Exception:
            # Логирование можно добавить позже; сейчас нотификация не критична.
            return



