from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Broadcast, BroadcastMessage, BroadcastStatus, User
from app.services.audit import log_admin_action
from app.storage.files import save_upload_file

router = APIRouter()


class BroadcastUpdateIn(BaseModel):
    title: str


class BroadcastReorderIn(BaseModel):
    ids_in_order: list[int]


def _bc_dict(b: Broadcast) -> dict:
    return {
        "id": b.id, "title": b.title, "status": b.status,
        "total_users": b.total_users, "sent_count": b.sent_count,
        "failed_count": b.failed_count,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "sent_at": b.sent_at.isoformat() if b.sent_at else None,
    }


def _msg_dict(m: BroadcastMessage) -> dict:
    return {
        "id": m.id, "broadcast_id": m.broadcast_id, "position": m.position,
        "message_type": m.message_type, "text": m.text,
        "parse_mode": m.parse_mode, "file_path": m.file_path,
        "file_name": m.file_name, "mime_type": m.mime_type,
    }


@router.get("")
async def list_broadcasts(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(Broadcast).order_by(Broadcast.created_at.desc()))
    return [_bc_dict(b) for b in rows]


@router.post("")
async def create_broadcast(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = Broadcast(
        title="Новая рассылка",
        status=BroadcastStatus.draft,
        created_by_admin_id=current_admin.id,
        created_at=datetime.utcnow(),
    )
    db.add(b)
    await db.flush()
    await log_admin_action(
        db, current_admin.id, "broadcast.create", "broadcast",
        str(b.id), {"title": b.title},
    )
    await db.commit()
    return _bc_dict(b)


@router.get("/{bid}")
async def get_broadcast(
    bid: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    msgs = await db.scalars(
        select(BroadcastMessage)
        .where(BroadcastMessage.broadcast_id == bid)
        .order_by(BroadcastMessage.position.asc(), BroadcastMessage.id.asc())
    )
    result = _bc_dict(b)
    result["messages"] = [_msg_dict(m) for m in msgs]
    return result


@router.put("/{bid}")
async def update_broadcast(
    bid: int,
    payload: BroadcastUpdateIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if b.status != BroadcastStatus.draft:
        raise HTTPException(status_code=400, detail="Можно редактировать только черновики")
    b.title = payload.title
    await log_admin_action(
        db, current_admin.id, "broadcast.update", "broadcast",
        str(bid), {"title": payload.title},
    )
    await db.commit()
    return {"ok": True}


@router.delete("/{bid}")
async def delete_broadcast(
    bid: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if b.status == BroadcastStatus.sending:
        raise HTTPException(status_code=400, detail="Нельзя удалить рассылку во время отправки")
    msgs = await db.scalars(
        select(BroadcastMessage).where(BroadcastMessage.broadcast_id == bid)
    )
    for m in msgs:
        await db.delete(m)
    await db.delete(b)
    await log_admin_action(
        db, current_admin.id, "broadcast.delete", "broadcast", str(bid), {},
    )
    await db.commit()
    return {"ok": True}


# --- Messages ---


@router.post("/{bid}/messages")
async def add_message(
    bid: int,
    message_type: str = Form("text"),
    text: str = Form(""),
    parse_mode: str = Form("HTML"),
    file: UploadFile | None = File(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    b = await db.get(Broadcast, bid)
    if not b or b.status != BroadcastStatus.draft:
        raise HTTPException(status_code=400, detail="Нельзя редактировать")
    last = await db.scalar(
        select(BroadcastMessage.position)
        .where(BroadcastMessage.broadcast_id == bid)
        .order_by(BroadcastMessage.position.desc())
    )
    file_path = file_name = mime_type = None
    if file and file.filename:
        file_path, _ = await save_upload_file(file)
        file_name = file.filename
        mime_type = file.content_type
    msg = BroadcastMessage(
        broadcast_id=bid,
        position=(last + 1) if last is not None else 0,
        message_type=message_type,
        text=text or None,
        parse_mode=parse_mode,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    await db.flush()
    await db.commit()
    return _msg_dict(msg)


@router.put("/{bid}/messages/{msg_id}")
async def update_message(
    bid: int,
    msg_id: int,
    message_type: str = Form("text"),
    text: str = Form(""),
    parse_mode: str = Form("HTML"),
    file: UploadFile | None = File(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    b = await db.get(Broadcast, bid)
    if not b or b.status != BroadcastStatus.draft:
        raise HTTPException(status_code=400, detail="Нельзя редактировать")
    msg = await db.get(BroadcastMessage, msg_id)
    if not msg or msg.broadcast_id != bid:
        raise HTTPException(status_code=404, detail="Блок не найден")
    msg.message_type = message_type
    msg.text = text or None
    msg.parse_mode = parse_mode
    if file and file.filename:
        file_path, _ = await save_upload_file(file)
        msg.file_path = file_path
        msg.file_name = file.filename
        msg.mime_type = file.content_type
    await db.commit()
    return _msg_dict(msg)


@router.delete("/{bid}/messages/{msg_id}")
async def delete_message(
    bid: int,
    msg_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    b = await db.get(Broadcast, bid)
    if not b or b.status != BroadcastStatus.draft:
        raise HTTPException(status_code=400, detail="Нельзя редактировать")
    msg = await db.get(BroadcastMessage, msg_id)
    if not msg or msg.broadcast_id != bid:
        raise HTTPException(status_code=404, detail="Блок не найден")
    await db.delete(msg)
    await db.commit()
    return {"ok": True}


@router.post("/{bid}/messages/reorder")
async def reorder_messages(
    bid: int,
    payload: BroadcastReorderIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    b = await db.get(Broadcast, bid)
    if not b or b.status != BroadcastStatus.draft:
        raise HTTPException(status_code=400, detail="Нельзя редактировать")
    rows = await db.scalars(
        select(BroadcastMessage)
        .where(BroadcastMessage.broadcast_id == bid)
        .where(BroadcastMessage.id.in_(payload.ids_in_order))
    )
    msg_map = {m.id: m for m in rows}
    for pos, mid in enumerate(payload.ids_in_order):
        if mid in msg_map:
            msg_map[mid].position = pos
    await db.commit()
    return {"ok": True}


# --- Send ---


@router.post("/{bid}/send")
async def send_broadcast(
    bid: int,
    background_tasks: BackgroundTasks,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if b.status != BroadcastStatus.draft:
        raise HTTPException(status_code=400, detail="Рассылка уже отправлена или отправляется")
    user_count = await db.scalar(select(func.count()).select_from(User))
    if not user_count:
        raise HTTPException(status_code=400, detail="Нет пользователей для рассылки")
    msgs = await db.scalars(
        select(BroadcastMessage)
        .where(BroadcastMessage.broadcast_id == bid)
        .order_by(BroadcastMessage.position.asc())
    )
    messages_data = [_msg_dict(m) for m in msgs]
    if not messages_data:
        raise HTTPException(status_code=400, detail="Нет сообщений в рассылке")
    b.status = BroadcastStatus.sending
    b.total_users = user_count
    b.sent_count = 0
    b.failed_count = 0
    await log_admin_action(
        db, current_admin.id, "broadcast.send", "broadcast",
        str(bid), {"total_users": user_count},
    )
    await db.commit()
    from app.integrations.telegram_broadcast import run_broadcast
    background_tasks.add_task(run_broadcast, bid, messages_data)
    return {"ok": True, "total_users": user_count}


@router.get("/{bid}/status")
async def broadcast_status(
    bid: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    return _bc_dict(b)
