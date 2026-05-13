from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Broadcast, BroadcastFile, BroadcastMessage, BroadcastStatus
from app.services.audit import log_admin_action
from app.services.broadcast_segments import count_audience, get_segment_user_ids
from app.storage.files import save_upload_file

router = APIRouter()

MAX_BROADCAST_FILES = 10


class BroadcastUpdateIn(BaseModel):
    title: str | None = None
    target_segment: dict | None = None


class BroadcastReorderIn(BaseModel):
    ids_in_order: list[int]


class AudienceCountIn(BaseModel):
    segment: dict


class TestSendIn(BaseModel):
    telegram_ids: list[int]


class ScheduleIn(BaseModel):
    scheduled_at: str
    timezone: str = "Europe/Moscow"


class ButtonsUpdateIn(BaseModel):
    buttons_json: list | None = None


def _bc_dict(b: Broadcast) -> dict:
    return {
        "id": b.id, "title": b.title, "status": b.status,
        "target_segment": b.target_segment or {"type": "all"},
        "total_users": b.total_users, "sent_count": b.sent_count,
        "failed_count": b.failed_count,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "sent_at": b.sent_at.isoformat() if b.sent_at else None,
        "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
        "admin_timezone": b.admin_timezone,
    }


def _msg_dict(m: BroadcastMessage) -> dict:
    return {
        "id": m.id, "broadcast_id": m.broadcast_id, "position": m.position,
        "message_type": m.message_type, "text": m.text,
        "parse_mode": m.parse_mode, "file_path": m.file_path,
        "file_name": m.file_name, "mime_type": m.mime_type,
        "buttons_json": m.buttons_json,
    }


def _file_dict(f: BroadcastFile) -> dict:
    return {
        "id": f.id, "broadcast_id": f.broadcast_id, "position": f.position,
        "file_path": f.file_path, "file_name": f.file_name,
        "mime_type": f.mime_type, "media_type": f.media_type,
    }


def _detect_media_type(mime: str | None, filename: str | None) -> str:
    mime = (mime or "").lower()
    name = (filename or "").lower()
    if mime.startswith("image/gif") or name.endswith(".gif"):
        return "animation"
    if mime.startswith("image/"):
        return "photo"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "document"


async def _require_draft(db: AsyncSession, bid: int) -> Broadcast:
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if b.status not in (BroadcastStatus.draft, BroadcastStatus.scheduled):
        raise HTTPException(status_code=400, detail="Можно редактировать только черновики")
    return b


async def _get_broadcast_files(db: AsyncSession, bid: int) -> list[dict]:
    rows = await db.scalars(
        select(BroadcastFile)
        .where(BroadcastFile.broadcast_id == bid)
        .order_by(BroadcastFile.position.asc(), BroadcastFile.id.asc())
    )
    return [_file_dict(f) for f in rows]


# ---- List / CRUD ----


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


@router.post("/audience/count")
async def audience_count(
    payload: AudienceCountIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    return await count_audience(db, payload.segment)


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
    result["files"] = await _get_broadcast_files(db, bid)
    return result


@router.put("/{bid}")
async def update_broadcast(
    bid: int,
    payload: BroadcastUpdateIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await _require_draft(db, bid)
    changes: dict = {}
    if payload.title is not None:
        b.title = payload.title
        changes["title"] = payload.title
    if payload.target_segment is not None:
        b.target_segment = payload.target_segment
        changes["target_segment"] = payload.target_segment
    if changes:
        await log_admin_action(
            db, current_admin.id, "broadcast.update", "broadcast",
            str(bid), changes,
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
    for tbl in (BroadcastMessage, BroadcastFile):
        rows = await db.scalars(select(tbl).where(tbl.broadcast_id == bid))
        for r in rows:
            await db.delete(r)
    await db.delete(b)
    await log_admin_action(
        db, current_admin.id, "broadcast.delete", "broadcast", str(bid), {},
    )
    await db.commit()
    return {"ok": True}


# ---- Messages ----


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
    await _require_draft(db, bid)
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
    buttons_json: str = Form(""),
    file: UploadFile | None = File(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    await _require_draft(db, bid)
    msg = await db.get(BroadcastMessage, msg_id)
    if not msg or msg.broadcast_id != bid:
        raise HTTPException(status_code=404, detail="Блок не найден")
    old_type = msg.message_type
    msg.message_type = message_type
    msg.text = text or None
    msg.parse_mode = parse_mode
    if buttons_json:
        import json
        try:
            msg.buttons_json = json.loads(buttons_json)
        except (json.JSONDecodeError, TypeError):
            msg.buttons_json = None
    else:
        msg.buttons_json = None
    if file and file.filename:
        file_path, _ = await save_upload_file(file)
        msg.file_path = file_path
        msg.file_name = file.filename
        msg.mime_type = file.content_type
    elif old_type != message_type:
        msg.file_path = None
        msg.file_name = None
        msg.mime_type = None
    await db.commit()
    return _msg_dict(msg)


@router.put("/{bid}/messages/{msg_id}/buttons")
async def update_message_buttons(
    bid: int,
    msg_id: int,
    payload: ButtonsUpdateIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    await _require_draft(db, bid)
    msg = await db.get(BroadcastMessage, msg_id)
    if not msg or msg.broadcast_id != bid:
        raise HTTPException(status_code=404, detail="Блок не найден")
    msg.buttons_json = payload.buttons_json
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
    await _require_draft(db, bid)
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
    await _require_draft(db, bid)
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


# ---- Files (multiple media) ----


@router.post("/{bid}/files")
async def upload_file(
    bid: int,
    file: UploadFile = File(...),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    await _require_draft(db, bid)
    cnt = await db.scalar(
        select(func.count()).select_from(BroadcastFile)
        .where(BroadcastFile.broadcast_id == bid)
    )
    if cnt >= MAX_BROADCAST_FILES:
        raise HTTPException(status_code=400, detail=f"Максимум {MAX_BROADCAST_FILES} файлов")
    file_path, _ = await save_upload_file(file)
    media_type = _detect_media_type(file.content_type, file.filename)
    last_pos = await db.scalar(
        select(BroadcastFile.position)
        .where(BroadcastFile.broadcast_id == bid)
        .order_by(BroadcastFile.position.desc())
    )
    bf = BroadcastFile(
        broadcast_id=bid,
        position=(last_pos + 1) if last_pos is not None else 0,
        file_path=file_path,
        file_name=file.filename or "file",
        mime_type=file.content_type,
        media_type=media_type,
        created_at=datetime.utcnow(),
    )
    db.add(bf)
    await db.flush()
    await db.commit()
    return _file_dict(bf)


@router.delete("/{bid}/files/{fid}")
async def delete_file(
    bid: int,
    fid: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    await _require_draft(db, bid)
    bf = await db.get(BroadcastFile, fid)
    if not bf or bf.broadcast_id != bid:
        raise HTTPException(status_code=404, detail="Файл не найден")
    await db.delete(bf)
    await db.commit()
    return {"ok": True}


@router.post("/{bid}/files/reorder")
async def reorder_files(
    bid: int,
    payload: BroadcastReorderIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    await _require_draft(db, bid)
    rows = await db.scalars(
        select(BroadcastFile)
        .where(BroadcastFile.broadcast_id == bid)
        .where(BroadcastFile.id.in_(payload.ids_in_order))
    )
    file_map = {f.id: f for f in rows}
    for pos, fid in enumerate(payload.ids_in_order):
        if fid in file_map:
            file_map[fid].position = pos
    await db.commit()
    return {"ok": True}


# ---- Test Send ----


@router.post("/{bid}/test-send")
async def test_send(
    bid: int,
    payload: TestSendIn,
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
        .order_by(BroadcastMessage.position.asc())
    )
    messages_data = [_msg_dict(m) for m in msgs]
    files_data = await _get_broadcast_files(db, bid)
    from app.integrations.telegram_broadcast import test_send_broadcast
    result = await test_send_broadcast(messages_data, files_data, payload.telegram_ids)
    return result


# ---- Send / Schedule ----


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
    if b.status not in (BroadcastStatus.draft, BroadcastStatus.scheduled):
        raise HTTPException(status_code=400, detail="Рассылка уже отправлена или отправляется")
    segment = b.target_segment or {"type": "all"}
    user_pairs = await get_segment_user_ids(db, segment)
    if not user_pairs:
        raise HTTPException(status_code=400, detail="Нет пользователей для рассылки")
    telegram_ids = [tg_id for _, tg_id in user_pairs]
    msgs = await db.scalars(
        select(BroadcastMessage)
        .where(BroadcastMessage.broadcast_id == bid)
        .order_by(BroadcastMessage.position.asc())
    )
    messages_data = [_msg_dict(m) for m in msgs]
    files_data = await _get_broadcast_files(db, bid)
    if not messages_data and not files_data:
        raise HTTPException(status_code=400, detail="Нет сообщений в рассылке")
    b.status = BroadcastStatus.sending
    b.total_users = len(telegram_ids)
    b.sent_count = 0
    b.failed_count = 0
    b.scheduled_at = None
    await log_admin_action(
        db, current_admin.id, "broadcast.send", "broadcast",
        str(bid), {"total_users": len(telegram_ids), "segment": segment},
    )
    await db.commit()
    from app.integrations.telegram_broadcast import run_broadcast
    background_tasks.add_task(run_broadcast, bid, messages_data, files_data, telegram_ids)
    return {"ok": True, "total_users": len(telegram_ids)}


@router.post("/{bid}/schedule")
async def schedule_broadcast(
    bid: int,
    payload: ScheduleIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if b.status not in (BroadcastStatus.draft, BroadcastStatus.scheduled):
        raise HTTPException(status_code=400, detail="Нельзя запланировать")
    try:
        tz = ZoneInfo(payload.timezone)
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail=f"Неизвестный часовой пояс: {payload.timezone}")
    try:
        local_dt = datetime.fromisoformat(payload.scheduled_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты")
    utc_dt = local_dt.replace(tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    if utc_dt <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Время должно быть в будущем")

    msgs = await db.scalars(
        select(BroadcastMessage)
        .where(BroadcastMessage.broadcast_id == bid)
        .order_by(BroadcastMessage.position.asc())
    )
    messages_data = [_msg_dict(m) for m in msgs]
    files_data = await _get_broadcast_files(db, bid)
    if not messages_data and not files_data:
        raise HTTPException(status_code=400, detail="Нет сообщений в рассылке")

    b.status = BroadcastStatus.scheduled
    b.scheduled_at = utc_dt
    b.admin_timezone = payload.timezone
    await log_admin_action(
        db, current_admin.id, "broadcast.schedule", "broadcast",
        str(bid), {"scheduled_at": utc_dt.isoformat(), "timezone": payload.timezone},
    )
    await db.commit()
    return {"ok": True, "scheduled_at": utc_dt.isoformat(), "timezone": payload.timezone}


@router.post("/{bid}/cancel-schedule")
async def cancel_schedule(
    bid: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    b = await db.get(Broadcast, bid)
    if not b:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    if b.status != BroadcastStatus.scheduled:
        raise HTTPException(status_code=400, detail="Рассылка не запланирована")
    b.status = BroadcastStatus.draft
    b.scheduled_at = None
    await log_admin_action(
        db, current_admin.id, "broadcast.cancel_schedule", "broadcast",
        str(bid), {},
    )
    await db.commit()
    return {"ok": True}


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
