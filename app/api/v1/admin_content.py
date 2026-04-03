from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, BotContent, ContentMenuItem, ContentVersion, MenuItemMessage
from app.services.audit import log_admin_action
from app.services.bot_texts import list_system_texts

router = APIRouter()


class ContentValueIn(BaseModel):
    value: str


class MenuItemIn(BaseModel):
    parent_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    icon: str | None = None
    item_type: str = "text"
    payload: str | None = None
    row: int = 0
    col: int = 0
    active: bool = True


class MenuReorderIn(BaseModel):
    items: list[dict]


@router.get("/texts")
async def list_texts(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(BotContent).order_by(BotContent.key))
    return [{"id": r.id, "key": r.key, "value": r.value, "updated_at": r.updated_at} for r in rows]


@router.get("/system-texts")
async def get_system_texts(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all system text definitions with current overrides."""
    _ = current_admin
    meta = list_system_texts()
    keys = [m["key"] for m in meta]
    rows = await db.scalars(select(BotContent).where(BotContent.key.in_(keys)))
    overrides = {r.key: {"value": r.value, "updated_at": r.updated_at} for r in rows}
    for item in meta:
        ovr = overrides.get(item["key"])
        item["current_value"] = ovr["value"] if ovr else None
        item["updated_at"] = ovr["updated_at"] if ovr else None
    return meta


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
        db, current_admin.id, "content.text.upsert", "bot_content", key,
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
    rows = await db.scalars(
        select(ContentMenuItem).order_by(
            ContentMenuItem.row.asc(), ContentMenuItem.col.asc(), ContentMenuItem.id.asc(),
        )
    )
    return [
        {
            "id": m.id,
            "parent_id": m.parent_id,
            "title": m.title,
            "icon": m.icon,
            "item_type": m.item_type,
            "payload": m.payload,
            "position": m.position,
            "row": m.row,
            "col": m.col,
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
    data = payload.model_dump()
    data["position"] = data["row"] * 100 + data["col"]
    item = ContentMenuItem(**data)
    db.add(item)
    await db.flush()

    if item.item_type == "text" and not item.payload:
        item.payload = f"menu_{item.id}"

    await log_admin_action(
        db, current_admin.id, "content.menu.create", "content_menu_item",
        str(item.id), payload.model_dump(),
    )
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
        "parent_id": item.parent_id, "title": item.title, "icon": item.icon,
        "item_type": item.item_type, "payload": item.payload,
        "row": item.row, "col": item.col, "active": item.active,
    }

    content_changed = False
    for k, v in payload.model_dump().items():
        if k == "payload" and item.item_type == "text":
            continue
        old_val = getattr(item, k, None)
        setattr(item, k, v)
        if k in ("title", "icon") and old_val != v:
            content_changed = True

    item.position = item.row * 100 + item.col
    item.updated_at = datetime.utcnow()

    if item.item_type == "text" and not item.payload:
        item.payload = f"menu_{item.id}"

    if content_changed:
        await _invalidate_message_cache(db, item_id)

    await log_admin_action(
        db, current_admin.id, "content.menu.update", "content_menu_item",
        str(item.id), {"before": before, "after": payload.model_dump()},
    )
    await db.commit()
    return {"ok": True}


@router.post("/menu/reorder")
async def reorder_menu(
    payload: MenuReorderIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ids = [it["id"] for it in payload.items]
    rows = await db.scalars(select(ContentMenuItem).where(ContentMenuItem.id.in_(ids)))
    item_map = {r.id: r for r in rows}
    if len(item_map) != len(ids):
        raise HTTPException(status_code=400, detail="Некоторые id меню не найдены")

    now = datetime.utcnow()
    for entry in payload.items:
        m = item_map[entry["id"]]
        m.row = entry.get("row", 0)
        m.col = entry.get("col", 0)
        m.position = m.row * 100 + m.col
        m.updated_at = now

    db.add(
        ContentVersion(
            key="menu_order",
            value={"items": payload.items},
            created_by_admin_id=current_admin.id,
        )
    )
    await log_admin_action(
        db, current_admin.id, "content.menu.reorder", "content_menu", "root",
        {"items": payload.items},
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
    await log_admin_action(
        db, current_admin.id, "content.menu.delete", "content_menu_item",
        str(item_id), {"deleted": True},
    )
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
            "id": v.id, "key": v.key, "value": v.value,
            "created_at": v.created_at, "created_by_admin_id": v.created_by_admin_id,
        }
        for v in rows
    ]


async def _invalidate_message_cache(db: AsyncSession, menu_item_id: int) -> None:
    msgs = await db.scalars(
        select(MenuItemMessage).where(MenuItemMessage.menu_item_id == menu_item_id)
    )
    for msg in msgs:
        msg.cached_chat_id = None
        msg.cached_message_id = None
