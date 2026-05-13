import logging
import traceback
from datetime import datetime
from pathlib import Path

from arq import create_pool, cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.telegram_bot_factory import make_bot
from app.integrations.telegram_notify import notify_check_error, notify_check_ready
from app.models import Check, CheckStatus, CheckWorkerLog, File, SystemSetting, TemplateVersion, User
from app.services.check_pipeline import run_check_pipeline
from app.services.credits import spend_credits
from app.services.followups import process_pending_followups
from app.storage.files import fixed_output_download_name, save_json_report

logger = logging.getLogger(__name__)


def _load_report_json(storage_path: str) -> dict | None:
    try:
        p = Path(storage_path)
        if not p.exists():
            return None
        import json
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load report JSON from %s", storage_path)
        return None


def _add_log(session: AsyncSession, check_id: int, level: str, message: str) -> None:
    session.add(CheckWorkerLog(check_id=check_id, level=level, message=message[:4000]))


async def process_check_task(ctx: dict, check_id: int) -> dict:
    async with SessionLocal() as session:
        check = await session.get(Check, check_id)
        if not check:
            logger.error("Check %s not found in DB", check_id)
            return {"error": "check_not_found", "check_id": check_id}

        check.status = CheckStatus.running
        _add_log(session, check.id, "info", "Проверка запущена")
        await session.commit()

        try:
            result = await _run_pipeline(session, check)
            ok = result.get("ok", False)
            check.status = CheckStatus.done if ok else CheckStatus.error

            if ok:
                _add_log(session, check.id, "info", "Проверка завершена успешно")
                check_errors = result.get("check_errors", [])
                if not check_errors:
                    await spend_credits(
                        session,
                        user_id=check.user_id,
                        amount=1,
                        description=f"Проверка #{check.id}",
                        reference_type="check",
                        reference_id=check.id,
                    )
                else:
                    _add_log(
                        session, check.id, "warning",
                        f"Кредит не списан: {len(check_errors)} внутр. ошибок при проверке",
                    )
                for notice in result.get("pipeline_notices", []):
                    _add_log(session, check.id, "info", notice)
                for ce in check_errors:
                    _add_log(session, check.id, "warning", f"Проблема проверки: {ce}")
            else:
                error_msg = result.get("error") or "Неизвестная ошибка пайплайна"
                _add_log(session, check.id, "error", f"Проверка не удалась: {error_msg}")

        except Exception:
            tb = traceback.format_exc()
            logger.exception("Unhandled error in check %s", check_id)
            result = {"ok": False}
            check.status = CheckStatus.error
            _add_log(session, check.id, "error", f"Необработанное исключение:\n{tb}")

        check.finished_at = datetime.utcnow()
        await session.commit()

        try:
            user = await session.get(User, check.user_id)
            if user and user.telegram_id:
                if check.status == CheckStatus.done:
                    report_data = None
                    if check.result_report_id:
                        report_file = await session.get(File, check.result_report_id)
                        if report_file:
                            report_data = _load_report_json(report_file.storage_path)

                    fixed_path = None
                    fixed_name = None
                    if check.output_file_id:
                        out_f = await session.get(File, check.output_file_id)
                        if out_f:
                            p = Path(out_f.storage_path)
                            if p.is_file():
                                fixed_path = str(p)
                                fixed_name = out_f.original_name

                    await notify_check_ready(
                        user.telegram_id,
                        check.id,
                        report=report_data,
                        fixed_doc_path=fixed_path,
                        fixed_doc_filename=fixed_name,
                    )
                elif check.status == CheckStatus.error:
                    await notify_check_error(user.telegram_id, check.id)
        except Exception:
            logger.exception("Failed to notify user about check %s", check_id)

        return {"check_id": check_id, "status": check.status.value if hasattr(check.status, "value") else check.status}


async def _run_pipeline(session: AsyncSession, check: Check) -> dict:
    input_file = await session.get(File, check.input_file_id)
    template_version = await session.get(TemplateVersion, check.template_version_id)

    if not input_file:
        return {"ok": False, "error": f"Input file (id={check.input_file_id}) not found in DB"}
    if not template_version:
        return {"ok": False, "error": f"Template version (id={check.template_version_id}) not found in DB"}

    admin_cfg_row = await session.get(SystemSetting, "autofix_global")
    admin_autofix_config = admin_cfg_row.value if admin_cfg_row else None

    pipeline_result = await run_check_pipeline(
        input_file.storage_path, template_version.rules_json,
        admin_autofix_config=admin_autofix_config,
    )

    if not pipeline_result.get("ok"):
        return {
            "ok": False,
            "error": pipeline_result.get("error", "Pipeline returned ok=False"),
            "pipeline_notices": pipeline_result.get("pipeline_notices", []),
        }

    report = pipeline_result.get("report") or {}
    check_errors = report.get("check_errors", [])

    report_path, report_size = save_json_report(report)
    report_file = File(
        storage_path=report_path,
        original_name=f"report_{check.id}.json",
        mime="application/json",
        size=report_size,
    )
    session.add(report_file)
    await session.flush()
    check.result_report_id = report_file.id

    output_docx_path = pipeline_result.get("output_docx_path")
    if output_docx_path:
        output_path = Path(output_docx_path)
        if output_path.exists():
            output_file = File(
                storage_path=str(output_path),
                original_name=fixed_output_download_name(input_file.original_name),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                size=output_path.stat().st_size,
            )
            session.add(output_file)
            await session.flush()
            check.output_file_id = output_file.id

    return {
        "ok": True,
        "pipeline_notices": pipeline_result.get("pipeline_notices", []),
        "check_errors": check_errors,
    }


async def run_followups_cron(ctx: dict) -> dict:
    """Periodic task: send pending follow-up messages."""
    if not settings.telegram_bot_token:
        return {"sent": 0, "reason": "no_bot_token"}
    bot = make_bot()
    try:
        sent = await process_pending_followups(bot)
    finally:
        await bot.session.close()
    if sent:
        logger.info("Follow-ups cron: sent %d messages", sent)
    return {"sent": sent}


async def send_scheduled_broadcasts_cron(ctx: dict) -> dict:
    """Check for scheduled broadcasts that are due and send them."""
    from sqlalchemy import select as sa_select

    from app.models import Broadcast, BroadcastFile, BroadcastMessage, BroadcastStatus
    from app.services.broadcast_segments import get_segment_user_ids

    now = datetime.utcnow()
    sent_count = 0

    async with SessionLocal() as db:
        rows = await db.scalars(
            sa_select(Broadcast).where(
                Broadcast.status == BroadcastStatus.scheduled,
                Broadcast.scheduled_at.isnot(None),
                Broadcast.scheduled_at <= now,
            )
        )
        due = list(rows)

        for b in due:
            try:
                segment = b.target_segment or {"type": "all"}
                user_pairs = await get_segment_user_ids(db, segment)
                if not user_pairs:
                    b.status = BroadcastStatus.failed
                    await db.commit()
                    continue

                telegram_ids = [tg_id for _, tg_id in user_pairs]
                msgs = await db.scalars(
                    sa_select(BroadcastMessage)
                    .where(BroadcastMessage.broadcast_id == b.id)
                    .order_by(BroadcastMessage.position.asc())
                )
                messages_data = []
                for m in msgs:
                    messages_data.append({
                        "id": m.id, "broadcast_id": m.broadcast_id,
                        "position": m.position, "message_type": m.message_type,
                        "text": m.text, "parse_mode": m.parse_mode,
                        "file_path": m.file_path, "file_name": m.file_name,
                        "mime_type": m.mime_type, "buttons_json": m.buttons_json,
                    })
                file_rows = await db.scalars(
                    sa_select(BroadcastFile)
                    .where(BroadcastFile.broadcast_id == b.id)
                    .order_by(BroadcastFile.position.asc())
                )
                files_data = []
                for f in file_rows:
                    files_data.append({
                        "id": f.id, "broadcast_id": f.broadcast_id,
                        "position": f.position, "file_path": f.file_path,
                        "file_name": f.file_name, "mime_type": f.mime_type,
                        "media_type": f.media_type,
                    })

                b.status = BroadcastStatus.sending
                b.total_users = len(telegram_ids)
                b.sent_count = 0
                b.failed_count = 0
                await db.commit()

                from app.integrations.telegram_broadcast import run_broadcast
                await run_broadcast(b.id, messages_data, files_data, telegram_ids)
                sent_count += 1
            except Exception:
                logger.exception("Failed to send scheduled broadcast %d", b.id)
                b.status = BroadcastStatus.failed
                await db.commit()

    if sent_count:
        logger.info("Scheduled broadcasts cron: sent %d broadcasts", sent_count)
    return {"sent": sent_count}


_redis_settings = RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    functions = [process_check_task]
    cron_jobs = [
        cron(run_followups_cron, minute=None, timeout=120),
        cron(send_scheduled_broadcasts_cron, minute=None, timeout=300),
    ]
    redis_settings = _redis_settings
    max_tries = 1
    job_timeout = 300


async def enqueue_check(check_id: int) -> None:
    redis = await create_pool(_redis_settings)
    try:
        await redis.enqueue_job("process_check_task", check_id)
    finally:
        await redis.close()
