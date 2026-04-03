from aiogram import Bot

from app.core.config import settings
from app.services.bot_texts import get_text


async def notify_check_ready(telegram_id: int, check_id: int) -> None:
    if not settings.telegram_bot_token:
        return

    text = await get_text("notify.check_done", check_id=check_id)
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
    finally:
        await bot.session.close()


