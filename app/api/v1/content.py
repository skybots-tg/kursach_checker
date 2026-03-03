from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, BotContent
from app.services.audit import log_admin_action

router = APIRouter()


class ContentUpdateRequest(BaseModel):
    value: str


@router.get("/public")
async def get_public_content(db: AsyncSession = Depends(get_db)) -> dict:
    rows = await db.scalars(select(BotContent))
    content = {r.key: r.value for r in rows}
    return {
        "about": content.get("about", "Сервис технической проверки оформления студенческих работ."),
        "faq": content.get("faq", "[\"Как оплатить?\", \"Какие форматы поддерживаются?\"]"),
    }


@router.get("/admin")
async def get_admin_content(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(BotContent).order_by(BotContent.id))
    return [{"id": r.id, "key": r.key, "value": r.value} for r in rows]


@router.put("/admin/{key}")
async def upsert_content(
    key: str,
    payload: ContentUpdateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not key.strip():
        raise HTTPException(status_code=400, detail="Ключ контента обязателен")

    item = await db.scalar(select(BotContent).where(BotContent.key == key))
    before = None
    if item:
        before = item.value
        item.value = payload.value
        item.updated_at = datetime.utcnow()
    else:
        item = BotContent(key=key, value=payload.value, updated_at=datetime.utcnow())
        db.add(item)

    await log_admin_action(
        db=db,
        admin_user_id=current_admin.id,
        action="content.upsert",
        entity_type="bot_content",
        entity_id=key,
        diff={"before": before, "after": payload.value},
    )
    await db.commit()
    return {"key": item.key, "value": item.value}
