from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Check, File, User

router = APIRouter()


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_obj = await db.get(File, file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="Файл не найден")

    allowed = await db.scalar(
        Check.__table__.select()
        .where(Check.user_id == current_user.id)
        .where(
            (Check.input_file_id == file_id)
            | (Check.result_report_id == file_id)
            | (Check.output_file_id == file_id)
        )
        .limit(1)
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Нет доступа к файлу")

    path = Path(file_obj.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Файл отсутствует на диске")

    return FileResponse(path=path, filename=file_obj.original_name, media_type=file_obj.mime)


