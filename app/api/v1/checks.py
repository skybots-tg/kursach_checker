import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File as FastFile, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Check, CheckStatus, CreditsBalance, File, TemplateVersion, User
from app.storage.files import save_upload_file
from app.workers.tasks import enqueue_check

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = FastFile(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".doc", ".docx"}:
        raise HTTPException(status_code=400, detail="Разрешены только DOC/DOCX")

    from app.core.config import settings as cfg
    max_bytes = cfg.max_upload_mb * 1024 * 1024
    path, size = await save_upload_file(file, max_bytes=max_bytes)
    entry = File(
        storage_path=path,
        original_name=file.filename or "document.docx",
        mime=file.content_type or "application/octet-stream",
        size=size,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"file_id": entry.id, "filename": entry.original_name, "size": entry.size}


@router.post("/start")
async def start_check(
    template_version_id: int,
    input_file_id: int,
    gost_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tv = await db.get(TemplateVersion, template_version_id)
    if not tv:
        raise HTTPException(status_code=404, detail="Версия шаблона не найдена")

    file_obj = await db.get(File, input_file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="Файл не найден")

    resolved_gost_id = gost_id
    if resolved_gost_id is None:
        from app.models import Gost
        first_gost = await db.scalar(
            select(Gost).where(Gost.active.is_(True)).order_by(Gost.id).limit(1)
        )
        if not first_gost:
            raise HTTPException(status_code=400, detail="Нет доступных ГОСТов")
        resolved_gost_id = first_gost.id

    credits = await db.get(CreditsBalance, current_user.id)
    if not credits or credits.credits_available < 1:
        raise HTTPException(status_code=402, detail="Недостаточно кредитов")

    check = Check(
        user_id=current_user.id,
        template_version_id=template_version_id,
        gost_id=resolved_gost_id,
        status=CheckStatus.queued,
        input_file_id=input_file_id,
    )
    db.add(check)
    await db.commit()

    await enqueue_check(check.id)
    return {"check_id": check.id, "status": getattr(check.status, 'value', check.status)}


@router.get("/{check_id}")
async def get_check(
    check_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    check = await db.get(Check, check_id)
    if not check or check.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Проверка не найдена")

    report_file = await db.get(File, check.result_report_id) if check.result_report_id else None
    output = await db.get(File, check.output_file_id) if check.output_file_id else None

    report_json = _load_report_json(report_file) if report_file else None

    return {
        "id": check.id,
        "status": getattr(check.status, 'value', check.status),
        "created_at": check.created_at,
        "finished_at": check.finished_at,
        "report_file_id": report_file.id if report_file else None,
        "output_file_id": output.id if output else None,
        "report": report_json,
    }


def _load_report_json(report_file: File) -> dict | None:
    try:
        p = Path(report_file.storage_path)
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
        findings = raw.get("findings", [])
        return {
            "findings": findings,
            "summary_errors": raw.get(
                "summary_errors",
                sum(1 for f in findings if f.get("severity") == "error"),
            ),
            "summary_warnings": raw.get(
                "summary_warnings",
                sum(1 for f in findings if f.get("severity") == "warning"),
            ),
            "summary_autofixed": raw.get(
                "summary_autofixed",
                sum(1 for f in findings if f.get("auto_fixed")),
            ),
        }
    except Exception:
        logger.exception("Failed to load report JSON from %s", report_file.storage_path)
        return None


@router.get("")
async def list_checks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.scalars(select(Check).where(Check.user_id == current_user.id).order_by(Check.id.desc()))
    return [
        {
            "id": r.id,
            "status": getattr(r.status, 'value', r.status),
            "created_at": r.created_at,
            "finished_at": r.finished_at,
            "template_version_id": r.template_version_id,
            "result_report_file_id": r.result_report_id,
            "output_file_id": r.output_file_id,
        }
        for r in rows
    ]
