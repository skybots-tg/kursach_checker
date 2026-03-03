from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, BotContent, ContentMenuItem, ContentVersion
from app.services.audit import log_admin_action

router = APIRouter()


class ContentValueIn(BaseModel):
    value: str


class MenuItemIn(BaseModel):
    parent_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    icon: str | None = None
    item_type: str = "text"
    payload: str | None = None
    position: int = 0
    active: bool = True


class MenuReorderIn(BaseModel):
    ids_in_order: list[int]


@router.get("/texts")
async def list_texts(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(BotContent).order_by(BotContent.key))
    return [{"id": r.id, "key": r.key, "value": r.value, "updated_at": r.updated_at} for r in rows]


@router.put("/texts/{key}")
async def upsert_text(
    key: str,
    payload: ContentValueIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.scalar(select(BotContent).where(BotContent.key == key))
    before = None
    if not item:
        item = BotContent(key=key, value=payload.value)
        db.add(item)
    else:
        before = item.value
        item.value = payload.value
        item.updated_at = datetime.utcnow()

    db.add(
        ContentVersion(
            key=key,
            value={"before": before, "after": payload.value},
            created_by_admin_id=current_admin.id,
        )
    )
    await log_admin_action(
        db,
        current_admin.id,
        "content.text.upsert",
        "bot_content",
        key,
        {"before": before, "after": payload.value},
    )
    await db.commit()
    return {"ok": True}


@router.get("/menu")
async def list_menu(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(ContentMenuItem).order_by(ContentMenuItem.position.asc(), ContentMenuItem.id.asc()))
    return [
        {
            "id": m.id,
            "parent_id": m.parent_id,
            "title": m.title,
            "icon": m.icon,
            "item_type": m.item_type,
            "payload": m.payload,
            "position": m.position,
            "active": m.active,
        }
        for m in rows
    ]


@router.post("/menu")
async def create_menu_item(
    payload: MenuItemIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = ContentMenuItem(**payload.model_dump())
    db.add(item)
    await db.flush()
    await log_admin_action(db, current_admin.id, "content.menu.create", "content_menu_item", str(item.id), payload.model_dump())
    await db.commit()
    return {"id": item.id}


@router.put("/menu/{item_id}")
async def update_menu_item(
    item_id: int,
    payload: MenuItemIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(ContentMenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Пункт меню не найден")

    before = {
        "parent_id": item.parent_id,
        "title": item.title,
        "icon": item.icon,
        "item_type": item.item_type,
        "payload": item.payload,
        "position": item.position,
        "active": item.active,
    }
    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()

    await log_admin_action(
        db,
        current_admin.id,
        "content.menu.update",
        "content_menu_item",
        str(item.id),
        {"before": before, "after": payload.model_dump()},
    )
    await db.commit()
    return {"ok": True}


@router.post("/menu/reorder")
async def reorder_menu(
    payload: MenuReorderIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = await db.scalars(select(ContentMenuItem).where(ContentMenuItem.id.in_(payload.ids_in_order)))
    item_map = {r.id: r for r in rows}
    if len(item_map) != len(payload.ids_in_order):
        raise HTTPException(status_code=400, detail="Некоторые id меню не найдены")

    for pos, item_id in enumerate(payload.ids_in_order):
        item_map[item_id].position = pos
        item_map[item_id].updated_at = datetime.utcnow()

    db.add(
        ContentVersion(
            key="menu_order",
            value={"ids_in_order": payload.ids_in_order},
            created_by_admin_id=current_admin.id,
        )
    )
    await log_admin_action(
        db,
        current_admin.id,
        "content.menu.reorder",
        "content_menu",
        "root",
        {"ids_in_order": payload.ids_in_order},
    )
    await db.commit()
    return {"ok": True}


@router.delete("/menu/{item_id}")
async def delete_menu_item(
    item_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(ContentMenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Пункт меню не найден")
    await db.delete(item)
    await log_admin_action(db, current_admin.id, "content.menu.delete", "content_menu_item", str(item_id), {"deleted": True})
    await db.commit()
    return {"ok": True}


@router.get("/versions")
async def list_content_versions(
    key: str | None = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    stmt = select(ContentVersion).order_by(ContentVersion.id.desc())
    if key:
        stmt = stmt.where(ContentVersion.key == key)
    rows = await db.scalars(stmt.limit(200))
    return [
        {
            "id": v.id,
            "key": v.key,
            "value": v.value,
            "created_at": v.created_at,
            "created_by_admin_id": v.created_by_admin_id,
        }
        for v in rows
    ]

