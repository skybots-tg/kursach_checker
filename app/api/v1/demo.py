"""Public demo endpoint — returns an active DemoSample as a CheckDetailResponse."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import DemoSample

router = APIRouter()


@router.get("")
async def get_demo(db: AsyncSession = Depends(get_db)) -> dict:
    sample = await db.scalar(
        select(DemoSample)
        .where(DemoSample.active.is_(True))
        .order_by(func.random())
        .limit(1)
    )
    if not sample:
        raise HTTPException(status_code=404, detail="Демо-проверка не найдена")

    report = sample.report_json or {}
    findings = report.get("findings", [])

    return {
        "id": 0,
        "status": "done",
        "created_at": sample.created_at.isoformat(),
        "finished_at": sample.created_at.isoformat(),
        "report_file_id": None,
        "output_file_id": sample.document_file_id,
        "report": {
            "findings": findings,
            "summary_errors": report.get(
                "summary_errors",
                sum(1 for f in findings if f.get("severity") == "error"),
            ),
            "summary_warnings": report.get(
                "summary_warnings",
                sum(1 for f in findings if f.get("severity") == "warning"),
            ),
            "summary_autofixed": report.get(
                "summary_autofixed",
                sum(1 for f in findings if f.get("auto_fixed")),
            ),
        },
    }
