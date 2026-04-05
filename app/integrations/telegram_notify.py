import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from app.core.config import settings
from app.services.bot_texts import get_text

logger = logging.getLogger(__name__)


async def notify_check_ready(
    telegram_id: int,
    check_id: int,
    *,
    fixed_doc_path: str | None = None,
    fixed_doc_filename: str | None = None,
) -> None:
    """Сообщение о готовности проверки; при наличии пути — дублируем исправленный DOCX в Telegram."""
    if not settings.telegram_bot_token:
        return

    text = await get_text("notify.check_done", check_id=check_id)
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
        if fixed_doc_path and fixed_doc_filename:
            path = Path(fixed_doc_path)
            if path.is_file():
                try:
                    caption = await get_text("check.fixed_doc_caption")
                    await bot.send_document(
                        chat_id=telegram_id,
                        document=FSInputFile(str(path), filename=fixed_doc_filename),
                        caption=caption,
                    )
                except Exception:
                    logger.exception(
                        "Failed to send fixed document to telegram_id=%s check_id=%s",
                        telegram_id,
                        check_id,
                    )
    finally:
        await bot.session.close()


