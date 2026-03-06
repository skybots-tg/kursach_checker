from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models_domain import Check, File, TemplateVersion
from backend.rules_engine.findings import CheckReport


class ChecksService:
    """Создание проверок, списание кредитов и доступ к отчётам."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_check(
        self,
        user_id: int,
        template_version_id: int,
        gost_id: int | None,
        input_file_id: int,
    ) -> Check:
        stmt_tv = select(TemplateVersion).where(TemplateVersion.id == template_version_id)
        result_tv = await self.session.execute(stmt_tv)
        template_version = result_tv.scalar_one()

        stmt_file = select(File).where(File.id == input_file_id)
        result_file = await self.session.execute(stmt_file)
        _ = result_file.scalar_one()

        check = Check(
            user_id=user_id,
            template_version_id=template_version.id,
            gost_id=gost_id,
            input_file_id=input_file_id,
            status="queued",
        )
        self.session.add(check)
        await self.session.flush()
        return check

    async def attach_report(
        self,
        check_id: int,
        report_file_id: int,
        output_file_id: int | None,
        report: CheckReport | None = None,
    ) -> None:
        stmt = select(Check).where(Check.id == check_id).with_for_update()
        result = await self.session.execute(stmt)
        check = result.scalar_one()

        check.result_report_id = report_file_id
        check.output_file_id = output_file_id
        check.status = "done"
        check.finished_at = datetime.utcnow()
        await self.session.flush()







