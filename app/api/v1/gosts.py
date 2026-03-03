from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Gost

router = APIRouter()


class GostIn(BaseModel):
    name: str
    description: str | None = None
    active: bool = True


@router.get("")
async def list_gosts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await db.scalars(select(Gost).where(Gost.active.is_(True)).order_by(Gost.id))
    return [{"id": r.id, "name": r.name, "description": r.description, "active": r.active} for r in rows]


@router.post("")
async def create_gost(payload: GostIn, db: AsyncSession = Depends(get_db)) -> dict:
    item = Gost(name=payload.name, description=payload.description, active=payload.active)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "name": item.name, "description": item.description, "active": item.active}
