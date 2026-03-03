from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import University

router = APIRouter()


class UniversityIn(BaseModel):
    name: str
    active: bool = True


@router.get("")
async def list_universities(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await db.scalars(select(University).where(University.active.is_(True)).order_by(University.id))
    return [{"id": r.id, "name": r.name, "active": r.active} for r in rows]


@router.post("")
async def create_university(payload: UniversityIn, db: AsyncSession = Depends(get_db)) -> dict:
    item = University(name=payload.name, active=payload.active)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "name": item.name, "active": item.active}
