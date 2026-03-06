from aiogram import Bot

from app.core.config import settings


async def notify_check_ready(telegram_id: int, check_id: int) -> None:
    if not settings.telegram_bot_token:
        return

    text = (
        "Проверка документа завершена.\n"
        f"ID проверки: {check_id}\n"
        "Откройте Mini App, чтобы посмотреть отчёт и скачать файлы."
    )
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
    finally:
        await bot.session.close()


