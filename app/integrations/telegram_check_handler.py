import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    Check,
    CheckStatus,
    CreditsBalance,
    File,
    Gost,
    Template,
    TemplateStatus,
    TemplateVersion,
    User,
)
from app.services.bot_texts import get_text
from app.storage.files import save_raw_file
from app.workers.tasks import enqueue_check

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".doc", ".docx"}
MAX_FILE_SIZE = settings.max_upload_mb * 1024 * 1024


async def handle_document(message: Message, bot: Bot) -> None:
    """Entry point: user sent a document to the bot.

    Validates the file, saves it, creates a Check record and enqueues
    the task to the shared worker — exactly the same path as the web app.
    """
    doc = message.document
    if not doc or not doc.file_name:
        return

    ext = Path(doc.file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        await message.reply(await get_text("check.only_doc_docx"))
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.reply(
            await get_text("check.file_too_big", max_mb=settings.max_upload_mb)
        )
        return

    telegram_id = message.from_user.id if message.from_user else None
    if not telegram_id:
        return

    async with SessionLocal() as db:
        user = await db.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        if not user:
            await message.reply(await get_text("check.need_start"))
            return

        credits = await db.get(CreditsBalance, user.id)
        if not credits or credits.credits_available < 1:
            await message.reply(
                await get_text("check.no_credits"), parse_mode="HTML",
            )
            return

        tv = await _get_default_template_version(db)
        if not tv:
            await message.reply(await get_text("check.no_templates"))
            return

        gost = await db.scalar(
            select(Gost).where(Gost.active.is_(True)).order_by(Gost.id).limit(1)
        )

        status_msg = await message.reply(await get_text("check.downloading"))

        try:
            tg_file = await bot.get_file(doc.file_id)
            file_bytes = await bot.download_file(tg_file.file_path)
        except Exception:
            logger.exception("Failed to download file from Telegram")
            await status_msg.edit_text(await get_text("check.download_failed"))
            return

        raw = file_bytes.read() if hasattr(file_bytes, "read") else file_bytes
        storage_path, size = save_raw_file(raw, ext)

        input_file = File(
            storage_path=storage_path,
            original_name=doc.file_name,
            mime=doc.mime_type or "application/octet-stream",
            size=size,
        )
        db.add(input_file)
        await db.flush()

        check = Check(
            user_id=user.id,
            template_version_id=tv.id,
            gost_id=gost.id if gost else None,
            status=CheckStatus.queued,
            input_file_id=input_file.id,
        )
        db.add(check)
        await db.commit()

        check_id = check.id

    await enqueue_check(check_id)
    await status_msg.edit_text(await get_text("check.queued"))


async def _get_default_template_version(db) -> TemplateVersion | None:
    """Pick the first active template's latest version."""
    template = await db.scalar(
        select(Template)
        .where(Template.status == TemplateStatus.published, Template.active.is_(True))
        .order_by(Template.id)
        .limit(1)
    )
    if not template:
        return None
    return await db.scalar(
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template.id)
        .order_by(TemplateVersion.version_number.desc())
        .limit(1)
    )
