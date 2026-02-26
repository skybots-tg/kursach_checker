from __future__ import annotations

"""
Async‑воркер для выполнения проверок документов.

Использует arq + Redis:
- принимает задачи по идентификатору проверки (check_id);
- загружает входной файл и конфиг шаблона;
- запускает rules engine;
- сохраняет отчёт и (при необходимости) исправленный документ;
- обновляет статус Check.
"""

import asyncio
from typing import Any

from arq import cron
from arq.connections import ArqRedis, RedisSettings, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db import AsyncSessionFactory
from backend.db.models_domain import Check, File, TemplateVersion
from backend.db.models_users import User
from backend.rules_engine.engine import run_checks
from backend.rules_engine.schemas import TemplateRulesConfig
from backend.storage.files import FileStorage
from backend.services.checks import ChecksService
from backend.integrations.telegram_bot import send_text_message


async def get_session() -> AsyncSession:
    return AsyncSessionFactory()


async def check_runner(ctx: dict[str, Any], check_id: int) -> None:
    """
    Основная задача: выполнить проверку для заданного check_id.
    """
    async with await get_session() as session:
        # Загружаем чек, входной файл и версию шаблона.
        stmt_check = select(Check).where(Check.id == check_id)
        result_check = await session.execute(stmt_check)
        check = result_check.scalar_one_or_none()
        if check is None:
            return

        stmt_tv = select(TemplateVersion).where(TemplateVersion.id == check.template_version_id)
        result_tv = await session.execute(stmt_tv)
        template_version = result_tv.scalar_one()

        rules = TemplateRulesConfig.model_validate(template_version.rules_json)

        stmt_file = select(File).where(File.id == check.input_file_id)
        result_file = await session.execute(stmt_file)
        input_file = result_file.scalar_one()

        storage = FileStorage(session)
        file_bytes = storage.open_file(input_file)

        # Запускаем rules engine (пока заглушка, см. engine.run_checks).
        report = await run_checks(
            template_version_id=template_version.id,
            rules=rules,
            file_bytes=file_bytes,
        )

        # Сохраняем отчёт в файловом хранилище.
        report_file = await storage.save_json(
            report.model_dump(mode="json"),
            original_name=f"check_{check.id}_report.json",
        )

        checks_service = ChecksService(session)
        await checks_service.attach_report(
            check_id=check.id,
            report_file_id=report_file.id,
            output_file_id=None,
            report=report,
        )

        await session.commit()

        # Пытаемся уведомить студента в Telegram, что проверка завершена.
        stmt_user = select(User).where(User.id == check.user_id)
        result_user = await session.execute(stmt_user)
        user = result_user.scalar_one_or_none()
        if user and user.telegram_id:
            await send_text_message(
                telegram_id=user.telegram_id,
                text=(
                    f"✅ Ваша проверка #{check.id} завершена.\n\n"
                    "Откройте Mini App через бота, чтобы посмотреть отчёт "
                    "и скачать исправленный документ (если он доступен)."
                ),
            )


class WorkerSettings:
    """
    Конфигурация arq‑воркера.
    """

    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.redis_dsn)

    functions = [check_runner]

    # Периодический пинг, если понадобится (можно подключить health‑метрики).
    cron_jobs = [
        # cron(dummy_job, second={0}),
    ]





