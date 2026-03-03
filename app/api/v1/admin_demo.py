from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, DemoSample

router = APIRouter()


class DemoSampleIn(BaseModel):
    name: str
    document_file_id: int | None = None
    report_json: dict
    active: bool = True


@router.get("")
async def list_demo_samples(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(DemoSample).order_by(DemoSample.id.desc()))
    return [
        {
            "id": d.id,
            "name": d.name,
            "document_file_id": d.document_file_id,
            "active": d.active,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
        for d in rows
    ]


@router.get("/{demo_id}")
async def get_demo_sample(
    demo_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    d = await db.get(DemoSample, demo_id)
    if not d:
        raise HTTPException(status_code=404, detail="Демо не найдено")
    return {
        "id": d.id,
        "name": d.name,
        "document_file_id": d.document_file_id,
        "report_json": d.report_json,
        "active": d.active,
    }


@router.post("")
async def create_demo_sample(
    payload: DemoSampleIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    item = DemoSample(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id}


@router.put("/{demo_id}")
async def update_demo_sample(
    demo_id: int,
    payload: DemoSampleIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    item = await db.get(DemoSample, demo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Демо не найдено")

    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}


@router.delete("/{demo_id}")
async def delete_demo_sample(
    demo_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    item = await db.get(DemoSample, demo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Демо не найдено")
    await db.delete(item)
    await db.commit()
    return {"ok": True}

