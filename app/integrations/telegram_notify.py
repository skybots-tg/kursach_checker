import logging
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.integrations.telegram_constants import CHECK_UPLOAD_NEW_CB
from app.services.bot_texts import get_text
from app.services.referrals import REFERRAL_BONUS_AMOUNT

logger = logging.getLogger(__name__)

# Payload пункта меню «Заказать полноценную работу» (см. миграцию
# alembic/versions/0012_content_rebrand.py). Совпадает со стандартным
# callback_data, которое разрешает custom_callback_handler в telegram_bot.py.
ORDER_FULL_PAYLOAD = "flow_order"


async def _build_done_keyboard() -> InlineKeyboardMarkup:
    menu = await get_text("notify.check_done_btn_menu")
    new_file = await get_text("notify.check_done_btn_new_file")
    order = await get_text("notify.check_done_btn_order")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=menu, callback_data="nav_home")],
            [InlineKeyboardButton(text=new_file, callback_data=CHECK_UPLOAD_NEW_CB)],
            [InlineKeyboardButton(text=order, callback_data=ORDER_FULL_PAYLOAD)],
        ]
    )


async def notify_check_ready(
    telegram_id: int,
    check_id: int,
    *,
    report: dict | None = None,
    fixed_doc_path: str | None = None,
    fixed_doc_filename: str | None = None,
) -> None:
    """Send the full check report and optional fixed DOCX to the user.

    Порядок сообщений:
    1. Подробный отчёт (если есть ``report``);
    2. Исправленный DOCX (если есть);
    3. Финальное «Готово ✅» с кнопками [Меню] / [Отправить новый файл] /
       [Заказать полноценную работу].
    """
    if not settings.telegram_bot_token:
        return

    bot = Bot(token=settings.telegram_bot_token)
    try:
        if report:
            report_text = await _format_report(report)
            await bot.send_message(
                chat_id=telegram_id, text=report_text, parse_mode="HTML",
            )

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

        done_text = await get_text("notify.check_done", check_id=check_id)
        keyboard = await _build_done_keyboard()
        await bot.send_message(
            chat_id=telegram_id,
            text=done_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    finally:
        await bot.session.close()


async def notify_check_error(
    telegram_id: int,
    check_id: int,
) -> None:
    """Notify the user that the check failed."""
    if not settings.telegram_bot_token:
        return

    text = await get_text("notify.check_error", check_id=check_id)
    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
    finally:
        await bot.session.close()


async def _format_report(report: dict) -> str:
    """Format the check report as a compact Telegram-friendly HTML message."""
    summary = report.get("summary", {})
    errors = summary.get("errors", 0)
    warnings = summary.get("warnings", 0)
    fixed = summary.get("fixed", 0)

    title = await get_text("report.title")
    lines = [title, ""]

    if errors == 0 and warnings == 0 and fixed == 0:
        lines.append(await get_text("report.no_issues"))
    elif errors == 0 and warnings == 0 and fixed > 0:
        lines.append(await get_text("report.all_fixed", fixed=fixed))
    else:
        lines.append(await get_text(
            "report.summary", errors=errors, warnings=warnings, fixed=fixed,
        ))

    findings = report.get("findings", [])
    unfixed = [
        f for f in findings
        if f.get("severity") in ("error", "warning") and not f.get("auto_fixed")
    ]
    auto_fixed = [
        f for f in findings
        if f.get("severity") in ("error", "warning") and f.get("auto_fixed")
    ]

    if unfixed:
        lines.append("")
        lines.append(await get_text("report.findings_header"))
        for i, f in enumerate(unfixed[:15], 1):
            icon = "\u274c" if f.get("severity") == "error" else "\u26a0\ufe0f"
            ftitle = f.get("title", "\u2014")
            found = f.get("found", "")
            line = f"{icon} {i}. <b>{_escape(ftitle)}</b>"
            if found:
                line += f"\n     {_escape(found)}"
            lines.append(line)

        remaining = len(unfixed) - 15
        if remaining > 0:
            lines.append(
                "\n" + await get_text("report.more_findings", count=remaining)
            )

    if auto_fixed:
        lines.append("")
        lines.append(await get_text("report.fixed_header"))
        for i, f in enumerate(auto_fixed[:10], 1):
            ftitle = f.get("title", "\u2014")
            lines.append(f"\u2705 {i}. {_escape(ftitle)}")

    return "\n".join(lines)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def notify_referral_bonus(inviter_telegram_id: int) -> None:
    """Сообщить инвайтеру о начисленном реферальном бонусе.

    Бонус фиксирован ``REFERRAL_BONUS_AMOUNT`` и выдаётся сразу при входе
    приглашённого друга в бота (не требует проверки).
    """
    if not settings.telegram_bot_token:
        return

    amount = REFERRAL_BONUS_AMOUNT
    word = "проверка" if amount == 1 else "проверки"
    text = (
        f"\U0001F525 <b>+{amount} бесплатная {word}</b>\n"
        "\n"
        "твой друг зашёл в бота по твоей реф-ссылке — "
        f"мы начислили тебе <b>+{amount} бесплатное пользование</b>.\n"
        "\n"
        f"зови ещё друзей — за каждого даём +{amount} \U0001F680"
    )

    bot = Bot(token=settings.telegram_bot_token)
    try:
        await bot.send_message(
            chat_id=inviter_telegram_id, text=text, parse_mode="HTML",
        )
    except Exception:
        logger.exception(
            "Failed to notify inviter telegram_id=%s about referral bonus",
            inviter_telegram_id,
        )
    finally:
        await bot.session.close()
