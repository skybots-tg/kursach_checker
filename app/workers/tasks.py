from datetime import datetime

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.telegram_notify import notify_check_ready
from app.models import Check, CheckStatus, File, TemplateVersion, User
from app.rules_engine.runner import run_document_checks
from app.storage.files import save_json_report


async def process_check_task(ctx: dict, check_id: int) -> dict:
    async with SessionLocal() as session:
        check = await session.get(Check, check_id)
        if not check:
            return {"error": "check_not_found", "check_id": check_id}

        check.status = CheckStatus.running
        await session.commit()

        result = await _run_pipeline(session, check)

        check.status = CheckStatus.done if result.get("ok") else CheckStatus.error
        check.finished_at = datetime.utcnow()
        await session.commit()

        user = await session.get(User, check.user_id)
        if user and user.telegram_id and check.status == CheckStatus.done:
            await notify_check_ready(user.telegram_id, check.id)

        return {"check_id": check_id, "status": check.status.value}


async def _run_pipeline(session: AsyncSession, check: Check) -> dict:
    input_file = await session.get(File, check.input_file_id)
    template_version = await session.get(TemplateVersion, check.template_version_id)
    if not input_file or not template_version:
        return {"ok": False}

    report = await run_document_checks(input_file.storage_path, template_version.rules_json)
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
    return {"ok": True}


class WorkerSettings:
    functions = [process_check_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)


async def enqueue_check(check_id: int) -> None:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("process_check_task", check_id)
