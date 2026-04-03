import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, Message

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
from app.services.check_pipeline import run_check_pipeline
from app.storage.files import save_json_report, save_raw_file

from sqlalchemy import select

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".doc", ".docx"}
MAX_FILE_SIZE = settings.max_upload_mb * 1024 * 1024


async def handle_document(message: Message, bot: Bot) -> None:
    """Entry point: user sent a document to the bot."""
    doc = message.document
    if not doc or not doc.file_name:
        return

    ext = Path(doc.file_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        await message.reply("Поддерживаются только файлы DOC и DOCX.")
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.reply(
            f"Файл слишком большой. Лимит — {settings.max_upload_mb} МБ."
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
            await message.reply("Сначала запустите бота командой /start.")
            return

        credits = await db.get(CreditsBalance, user.id)
        if not credits or credits.credits_available < 1:
            await message.reply("Недостаточно кредитов для проверки.")
            return

        tv = await _get_default_template_version(db)
        if not tv:
            await message.reply(
                "Нет активных шаблонов. Обратитесь к администратору."
            )
            return

        gost = await db.scalar(
            select(Gost).where(Gost.active.is_(True)).order_by(Gost.id).limit(1)
        )

        status_msg = await message.reply("⏳ Скачиваю файл…")

        try:
            tg_file = await bot.get_file(doc.file_id)
            file_bytes = await bot.download_file(tg_file.file_path)
        except Exception:
            logger.exception("Failed to download file from Telegram")
            await status_msg.edit_text("Не удалось скачать файл. Попробуйте ещё раз.")
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

        credits.credits_available -= 1
        credits.updated_at = datetime.utcnow()

        check = Check(
            user_id=user.id,
            template_version_id=tv.id,
            gost_id=gost.id if gost else None,
            status=CheckStatus.running,
            input_file_id=input_file.id,
        )
        db.add(check)
        await db.flush()
        await db.commit()

    await status_msg.edit_text("🔍 Проверяю документ…")

    try:
        result = await run_check_pipeline(storage_path, tv.rules_json)
    except Exception:
        logger.exception("Pipeline error for check %s", check.id)
        await _finalize_check(check.id, CheckStatus.error)
        await status_msg.edit_text("Произошла ошибка при проверке. Попробуйте позже.")
        return

    if not result.get("ok"):
        await _finalize_check(check.id, CheckStatus.error)
        error = result.get("error") or "Неизвестная ошибка"
        await status_msg.edit_text(f"Проверка не удалась: {error}")
        return

    report = result.get("report") or {}
    output_docx_path = result.get("output_docx_path")
    await _save_check_results(check.id, report, output_docx_path)

    text = _format_report(report)
    await status_msg.edit_text(text, parse_mode="HTML")

    if output_docx_path and Path(output_docx_path).exists():
        await bot.send_document(
            message.chat.id,
            FSInputFile(output_docx_path, filename=f"fixed_{doc.file_name}"),
            caption="Исправленный документ",
        )


async def _get_default_template_version(db) -> TemplateVersion | None:
    """Pick the first active template's latest version."""
    template = await db.scalar(
        select(Template)
        .where(Template.status == TemplateStatus.active)
        .order_by(Template.id)
        .limit(1)
    )
    if not template:
        return None
    return await db.scalar(
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template.id)
        .order_by(TemplateVersion.version.desc())
        .limit(1)
    )


async def _finalize_check(check_id: int, status: CheckStatus) -> None:
    async with SessionLocal() as db:
        check = await db.get(Check, check_id)
        if check:
            check.status = status
            check.finished_at = datetime.utcnow()
            await db.commit()


async def _save_check_results(
    check_id: int, report: dict, output_docx_path: str | None,
) -> None:
    async with SessionLocal() as db:
        check = await db.get(Check, check_id)
        if not check:
            return

        report_path, report_size = save_json_report(report)
        report_file = File(
            storage_path=report_path,
            original_name=f"report_{check_id}.json",
            mime="application/json",
            size=report_size,
        )
        db.add(report_file)
        await db.flush()
        check.result_report_id = report_file.id

        if output_docx_path:
            out = Path(output_docx_path)
            if out.exists():
                output_file = File(
                    storage_path=str(out),
                    original_name=f"check_{check_id}_fixed.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    size=out.stat().st_size,
                )
                db.add(output_file)
                await db.flush()
                check.output_file_id = output_file.id

        check.status = CheckStatus.done
        check.finished_at = datetime.utcnow()
        await db.commit()


def _format_report(report: dict) -> str:
    """Format the check report as a compact Telegram-friendly HTML message."""
    summary = report.get("summary", {})
    errors = summary.get("errors", 0)
    warnings = summary.get("warnings", 0)
    fixed = summary.get("fixed", 0)

    lines = ["<b>📋 Результат проверки</b>", ""]

    if errors == 0 and warnings == 0:
        lines.append("✅ Нарушений не обнаружено!")
    else:
        lines.append(f"❌ Ошибок: {errors}")
        lines.append(f"⚠️ Предупреждений: {warnings}")
        if fixed:
            lines.append(f"🔧 Автоисправлений: {fixed}")

    findings = report.get("findings", [])
    important = [
        f for f in findings
        if f.get("severity") in ("error", "warning")
    ]

    if important:
        lines.append("")
        lines.append("<b>Замечания:</b>")
        for i, f in enumerate(important[:15], 1):
            icon = "❌" if f.get("severity") == "error" else "⚠️"
            title = f.get("title", "—")
            found = f.get("found", "")
            line = f"{icon} {i}. <b>{_escape(title)}</b>"
            if found:
                line += f"\n     {_escape(found)}"
            lines.append(line)

        remaining = len(important) - 15
        if remaining > 0:
            lines.append(f"\n… и ещё {remaining} замечаний")

    return "\n".join(lines)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
