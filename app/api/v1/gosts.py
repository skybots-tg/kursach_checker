from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Gost

router = APIRouter()


class GostIn(BaseModel):
    name: str
    description: str | None = None
    university_id: int | None = None
    active: bool = True


def _gost_dict(r: Gost) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "university_id": r.university_id,
        "active": r.active,
    }


@router.get("")
async def list_gosts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await db.scalars(select(Gost).where(Gost.active.is_(True)).order_by(Gost.id))
    return [_gost_dict(r) for r in rows]


@router.post("")
async def create_gost(
    payload: GostIn,
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = Gost(
        name=payload.name,
        description=payload.description,
        university_id=payload.university_id,
        active=payload.active,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _gost_dict(item)


@router.put("/{gost_id}")
async def update_gost(
    gost_id: int,
    payload: GostIn,
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(Gost, gost_id)
    if not item:
        raise HTTPException(status_code=404, detail="ГОСТ не найден")
    item.name = payload.name
    item.description = payload.description
    item.university_id = payload.university_id
    item.active = payload.active
    await db.commit()
    await db.refresh(item)
    return _gost_dict(item)


@router.delete("/{gost_id}")
async def delete_gost(
    gost_id: int,
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(Gost, gost_id)
    if not item:
        raise HTTPException(status_code=404, detail="ГОСТ не найден")
    await db.delete(item)
    await db.commit()
    return {"ok": True}
