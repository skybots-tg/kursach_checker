import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Check, CheckWorkerLog, File, Gost, TemplateVersion, User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_checks(
    status: str | None = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    stmt = (
        select(Check, User, TemplateVersion, Gost)
        .join(User, User.id == Check.user_id)
        .join(TemplateVersion, TemplateVersion.id == Check.template_version_id)
        .outerjoin(Gost, Gost.id == Check.gost_id)
        .order_by(Check.id.desc())
    )
    if status:
        stmt = stmt.where(Check.status == status)

    rows = await db.execute(stmt)
    return [
        {
            "id": c.id,
            "status": getattr(c.status, 'value', c.status),
            "user": {"id": u.id, "telegram_id": u.telegram_id, "username": u.username},
            "user_id": u.id,
            "template_version_id": tv.id,
            "gost": {"id": g.id, "name": g.name} if g else None,
            "created_at": c.created_at,
            "finished_at": c.finished_at,
        }
        for c, u, tv, g in rows
    ]


@router.get("/{check_id}")
async def get_check_card(
    check_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    check = await db.get(Check, check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Проверка не найдена")

    user = await db.get(User, check.user_id)

    logs = await db.scalars(
        select(CheckWorkerLog)
        .where(CheckWorkerLog.check_id == check_id)
        .order_by(CheckWorkerLog.id.desc())
        .limit(200)
    )
    input_file = await db.get(File, check.input_file_id)
    report_file = await db.get(File, check.result_report_id) if check.result_report_id else None
    output_file = await db.get(File, check.output_file_id) if check.output_file_id else None

    report_summary = _load_report_summary(report_file) if report_file else None

    return {
        "check": {
            "id": check.id,
            "status": getattr(check.status, 'value', check.status),
            "user_id": check.user_id,
            "user": {"id": user.id, "telegram_id": user.telegram_id, "username": user.username} if user else None,
            "template_version_id": check.template_version_id,
            "gost_id": check.gost_id,
            "created_at": check.created_at,
            "finished_at": check.finished_at,
        },
        "files": {
            "input": _file_payload(input_file),
            "report": _file_payload(report_file),
            "output": _file_payload(output_file),
        },
        "report_summary": report_summary,
        "worker_logs": [
            {"id": l.id, "level": l.level, "message": l.message, "created_at": l.created_at}
            for l in logs
        ],
    }


@router.get("/stats/summary")
async def checks_summary(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    total = await db.scalar(select(func.count(Check.id)))
    errors = await db.scalar(select(func.count(Check.id)).where(Check.status == "error"))
    done = await db.scalar(select(func.count(Check.id)).where(Check.status == "done"))
    return {"total": int(total or 0), "done": int(done or 0), "errors": int(errors or 0)}


def _file_payload(file_obj: File | None) -> dict | None:
    if not file_obj:
        return None
    return {
        "id": file_obj.id,
        "name": file_obj.original_name,
        "mime": file_obj.mime,
        "size": file_obj.size,
        "created_at": file_obj.created_at,
    }


def _load_report_summary(report_file: File) -> dict | None:
    try:
        p = Path(report_file.storage_path)
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
        summary = raw.get("summary", {})
        findings = raw.get("findings", [])
        check_errors = raw.get("check_errors", [])
        return {
            "errors": summary.get("errors", 0),
            "warnings": summary.get("warnings", 0),
            "fixed": summary.get("fixed", 0),
            "findings_count": len(findings),
            "check_errors": check_errors,
        }
    except Exception:
        logger.exception("Failed to load report summary from %s", report_file.storage_path)
        return None


