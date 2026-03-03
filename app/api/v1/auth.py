from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_credits
from app.core.config import settings
from app.core.security import create_access_token, validate_telegram_init_data
from app.db.session import get_db
from app.models import CreditsBalance, User

router = APIRouter()


class TelegramAuthRequest(BaseModel):
    init_data: str


@router.post("/telegram")
async def auth_telegram(payload: TelegramAuthRequest, db: AsyncSession = Depends(get_db)) -> dict:
    tg_user = validate_telegram_init_data(payload.init_data, settings.telegram_bot_token)
    telegram_id = int(tg_user["id"])

    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name"),
            username=tg_user.get("username"),
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()
        db.add(CreditsBalance(user_id=user.id, credits_available=0))
    else:
        user.first_name = tg_user.get("first_name")
        user.username = tg_user.get("username")
        user.last_login_at = datetime.utcnow()

    await db.commit()
    token = create_access_token(user.id)
    credits = await get_user_credits(db, user.id)
    return {
        "message": "Авторизация успешна",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "username": user.username,
            "credits": credits,
        },
    }


@router.get("/me")
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    credits = await get_user_credits(db, current_user.id)
    return {
        "id": current_user.id,
        "telegram_id": current_user.telegram_id,
        "first_name": current_user.first_name,
        "username": current_user.username,
        "credits_available": credits,
    }
