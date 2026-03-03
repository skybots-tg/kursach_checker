from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File as FastFile, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Check, CheckStatus, CreditsBalance, File, TemplateVersion, User
from app.storage.files import save_upload_file
from app.workers.tasks import enqueue_check

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

    path, size = await save_upload_file(file)
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
    gost_id: int,
    input_file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tv = await db.get(TemplateVersion, template_version_id)
    if not tv:
        raise HTTPException(status_code=404, detail="Версия шаблона не найдена")

    file_obj = await db.get(File, input_file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="Файл не найден")

    credits = await db.get(CreditsBalance, current_user.id)
    if not credits or credits.credits_available < 1:
        raise HTTPException(status_code=402, detail="Недостаточно кредитов")

    credits.credits_available -= 1
    credits.updated_at = datetime.utcnow()

    check = Check(
        user_id=current_user.id,
        template_version_id=template_version_id,
        gost_id=gost_id,
        status=CheckStatus.queued,
        input_file_id=input_file_id,
    )
    db.add(check)
    await db.flush()
    await db.commit()

    await enqueue_check(check.id)
    return {"check_id": check.id, "status": check.status.value}


@router.get("/{check_id}")
async def get_check(
    check_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    check = await db.get(Check, check_id)
    if not check or check.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Проверка не найдена")

    report = await db.get(File, check.result_report_id) if check.result_report_id else None
    output = await db.get(File, check.output_file_id) if check.output_file_id else None
    return {
        "id": check.id,
        "status": check.status.value,
        "created_at": check.created_at,
        "finished_at": check.finished_at,
        "result_report_file_id": report.id if report else None,
        "output_file_id": output.id if output else None,
    }


@router.get("")
async def list_checks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.scalars(select(Check).where(Check.user_id == current_user.id).order_by(Check.id.desc()))
    return [
        {
            "id": r.id,
            "status": r.status.value,
            "created_at": r.created_at,
            "finished_at": r.finished_at,
            "template_version_id": r.template_version_id,
            "result_report_file_id": r.result_report_id,
            "output_file_id": r.output_file_id,
        }
        for r in rows
    ]
