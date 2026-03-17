from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import University

router = APIRouter()


class UniversityIn(BaseModel):
    name: str
    active: bool = True


def _uni_dict(r: University) -> dict:
    return {"id": r.id, "name": r.name, "active": r.active}


@router.get("")
async def list_universities(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await db.scalars(select(University).order_by(University.id))
    return [_uni_dict(r) for r in rows]


@router.post("")
async def create_university(payload: UniversityIn, db: AsyncSession = Depends(get_db)) -> dict:
    item = University(name=payload.name, active=payload.active)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _uni_dict(item)


@router.put("/{uni_id}")
async def update_university(uni_id: int, payload: UniversityIn, db: AsyncSession = Depends(get_db)) -> dict:
    item = await db.get(University, uni_id)
    if not item:
        raise HTTPException(status_code=404, detail="ВУЗ не найден")
    item.name = payload.name
    item.active = payload.active
    await db.commit()
    await db.refresh(item)
    return _uni_dict(item)


@router.delete("/{uni_id}")
async def delete_university(uni_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    item = await db.get(University, uni_id)
    if not item:
        raise HTTPException(status_code=404, detail="ВУЗ не найден")
    await db.delete(item)
    await db.commit()
    return {"ok": True}
