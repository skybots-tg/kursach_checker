import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_admin_token
from app.db.session import get_db
from app.models import AdminUser

__all__ = ["create_admin_token", "get_current_admin", "get_optional_admin", "require_role", "get_admin_by_login"]


async def get_optional_admin(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminUser | None:
    """Bearer с admin JWT — вернуть админа; иначе None (без 401). User JWT с другим секретом не пройдёт decode."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.admin_jwt_secret, algorithms=["HS256"])
        admin_id = int(payload["sub"])
    except Exception:  # noqa: BLE001
        return None
    # User JWT (тот же секрет в .env) не содержит role — не считаем это админом
    if payload.get("role") is None:
        return None
    admin = await db.get(AdminUser, admin_id)
    return admin


async def get_current_admin(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется admin авторизация")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.admin_jwt_secret, algorithms=["HS256"])
        admin_id = int(payload["sub"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Невалидный admin токен") from exc

    if payload.get("role") is None:
        raise HTTPException(status_code=401, detail="Невалидный admin токен")

    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise HTTPException(status_code=401, detail="Админ не найден")
    return admin


def require_role(admin: AdminUser, allowed: set[str]) -> None:
    if admin.role not in allowed:
        raise HTTPException(status_code=403, detail="Недостаточно прав")


async def get_admin_by_login(db: AsyncSession, login: str) -> AdminUser | None:
    return await db.scalar(select(AdminUser).where(AdminUser.login == login))


