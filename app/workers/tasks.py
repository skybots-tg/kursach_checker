import logging
import traceback
from datetime import datetime
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.telegram_notify import notify_check_ready
from app.models import Check, CheckStatus, CheckWorkerLog, File, TemplateVersion, User
from app.services.check_pipeline import run_check_pipeline
from app.services.credits import spend_credits
from app.storage.files import save_json_report

logger = logging.getLogger(__name__)


def _add_log(session: AsyncSession, check_id: int, level: str, message: str) -> None:
    session.add(CheckWorkerLog(check_id=check_id, level=level, message=message[:4000]))


async def process_check_task(ctx: dict, check_id: int) -> dict:
    async with SessionLocal() as session:
        check = await session.get(Check, check_id)
        if not check:
            logger.error("Check %s not found in DB", check_id)
            return {"error": "check_not_found", "check_id": check_id}

        check.status = CheckStatus.running
        _add_log(session, check.id, "info", "Check started")
        await session.commit()

        try:
            result = await _run_pipeline(session, check)
            ok = result.get("ok", False)
            check.status = CheckStatus.done if ok else CheckStatus.error

            if ok:
                _add_log(session, check.id, "info", "Check completed successfully")
                await spend_credits(
                    session,
                    user_id=check.user_id,
                    amount=1,
                    description=f"Check #{check.id}",
                    reference_type="check",
                    reference_id=check.id,
                )
                for notice in result.get("pipeline_notices", []):
                    _add_log(session, check.id, "info", f"Pipeline: {notice}")
                for ce in result.get("check_errors", []):
                    _add_log(session, check.id, "warning", f"Check issue: {ce}")
            else:
                error_msg = result.get("error") or "Unknown pipeline error"
                _add_log(session, check.id, "error", f"Check failed: {error_msg}")

        except Exception:
            tb = traceback.format_exc()
            logger.exception("Unhandled error in check %s", check_id)
            result = {"ok": False}
            check.status = CheckStatus.error
            _add_log(session, check.id, "error", f"Unhandled exception:\n{tb}")

        check.finished_at = datetime.utcnow()
        await session.commit()

        try:
            user = await session.get(User, check.user_id)
            if user and user.telegram_id and check.status == CheckStatus.done:
                await notify_check_ready(user.telegram_id, check.id)
        except Exception:
            logger.exception("Failed to notify user about check %s", check_id)

        return {"check_id": check_id, "status": check.status.value}


async def _run_pipeline(session: AsyncSession, check: Check) -> dict:
    input_file = await session.get(File, check.input_file_id)
    template_version = await session.get(TemplateVersion, check.template_version_id)

    if not input_file:
        return {"ok": False, "error": f"Input file (id={check.input_file_id}) not found in DB"}
    if not template_version:
        return {"ok": False, "error": f"Template version (id={check.template_version_id}) not found in DB"}

    pipeline_result = await run_check_pipeline(input_file.storage_path, template_version.rules_json)

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
                original_name=f"check_{check.id}_fixed.docx",
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


_redis_settings = RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    functions = [process_check_task]
    redis_settings = _redis_settings
    max_tries = 1
    job_timeout = 300


async def enqueue_check(check_id: int) -> None:
    redis = await create_pool(_redis_settings)
    try:
        await redis.enqueue_job("process_check_task", check_id)
    finally:
        await redis.close()
