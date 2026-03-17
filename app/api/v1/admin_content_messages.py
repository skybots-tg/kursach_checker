from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, ContentMenuItem, MenuItemMessage
from app.services.audit import log_admin_action
from app.storage.files import save_upload_file

router = APIRouter()


class MessageReorderIn(BaseModel):
    ids_in_order: list[int]


async def _get_menu_item(db: AsyncSession, item_id: int) -> ContentMenuItem:
    item = await db.get(ContentMenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Пункт меню не найден")
    return item


@router.get("/menu/{item_id}/messages")
async def list_messages(
    item_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    await _get_menu_item(db, item_id)
    rows = await db.scalars(
        select(MenuItemMessage)
        .where(MenuItemMessage.menu_item_id == item_id)
        .order_by(MenuItemMessage.position.asc(), MenuItemMessage.id.asc())
    )
    return [
        {
            "id": m.id,
            "menu_item_id": m.menu_item_id,
            "position": m.position,
            "message_type": m.message_type,
            "text": m.text,
            "parse_mode": m.parse_mode,
            "file_path": m.file_path,
            "file_name": m.file_name,
            "mime_type": m.mime_type,
        }
        for m in rows
    ]


@router.post("/menu/{item_id}/messages")
async def create_message(
    item_id: int,
    message_type: str = Form("text"),
    text: str = Form(""),
    parse_mode: str = Form("HTML"),
    file: UploadFile | None = File(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_menu_item(db, item_id)

    last = await db.scalar(
        select(MenuItemMessage.position)
        .where(MenuItemMessage.menu_item_id == item_id)
        .order_by(MenuItemMessage.position.desc())
    )
    next_pos = (last + 1) if last is not None else 0

    file_path = file_name = mime_type = None
    if file and file.filename:
        file_path, _ = await save_upload_file(file)
        file_name = file.filename
        mime_type = file.content_type

    now = datetime.utcnow()
    msg = MenuItemMessage(
        menu_item_id=item_id,
        position=next_pos,
        message_type=message_type,
        text=text or None,
        parse_mode=parse_mode,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        created_at=now,
        updated_at=now,
    )
    db.add(msg)
    await db.flush()

    await log_admin_action(
        db, current_admin.id, "content.message.create", "menu_item_message",
        str(msg.id), {"menu_item_id": item_id, "type": message_type},
    )
    await db.commit()
    return {"id": msg.id}


@router.put("/menu/{item_id}/messages/{msg_id}")
async def update_message(
    item_id: int,
    msg_id: int,
    message_type: str = Form("text"),
    text: str = Form(""),
    parse_mode: str = Form("HTML"),
    file: UploadFile | None = File(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_menu_item(db, item_id)
    msg = await db.get(MenuItemMessage, msg_id)
    if not msg or msg.menu_item_id != item_id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    msg.message_type = message_type
    msg.text = text or None
    msg.parse_mode = parse_mode

    if file and file.filename:
        file_path, _ = await save_upload_file(file)
        msg.file_path = file_path
        msg.file_name = file.filename
        msg.mime_type = file.content_type

    msg.cached_chat_id = None
    msg.cached_message_id = None
    msg.updated_at = datetime.utcnow()

    await log_admin_action(
        db, current_admin.id, "content.message.update", "menu_item_message",
        str(msg_id), {"menu_item_id": item_id, "type": message_type},
    )
    await db.commit()
    return {"ok": True}


@router.delete("/menu/{item_id}/messages/{msg_id}")
async def delete_message(
    item_id: int,
    msg_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    msg = await db.get(MenuItemMessage, msg_id)
    if not msg or msg.menu_item_id != item_id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    await db.delete(msg)
    await log_admin_action(
        db, current_admin.id, "content.message.delete", "menu_item_message",
        str(msg_id), {"menu_item_id": item_id},
    )
    await db.commit()
    return {"ok": True}


@router.post("/menu/{item_id}/messages/reorder")
async def reorder_messages(
    item_id: int,
    payload: MessageReorderIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_menu_item(db, item_id)
    rows = await db.scalars(
        select(MenuItemMessage)
        .where(MenuItemMessage.menu_item_id == item_id)
        .where(MenuItemMessage.id.in_(payload.ids_in_order))
    )
    msg_map = {m.id: m for m in rows}
    if len(msg_map) != len(payload.ids_in_order):
        raise HTTPException(status_code=400, detail="Некоторые id сообщений не найдены")

    now = datetime.utcnow()
    for pos, mid in enumerate(payload.ids_in_order):
        msg_map[mid].position = pos
        msg_map[mid].updated_at = now

    await log_admin_action(
        db, current_admin.id, "content.message.reorder", "menu_item_message",
        str(item_id), {"ids_in_order": payload.ids_in_order},
    )
    await db.commit()
    return {"ok": True}
