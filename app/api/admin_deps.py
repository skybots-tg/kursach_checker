import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models import AdminUser


def create_admin_token(admin_id: int, role: str) -> str:
    return jwt.encode({"sub": str(admin_id), "role": role}, settings.admin_jwt_secret, algorithm="HS256")


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

    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise HTTPException(status_code=401, detail="Админ не найден")
    return admin


def require_role(admin: AdminUser, allowed: set[str]) -> None:
    if admin.role not in allowed:
        raise HTTPException(status_code=403, detail="Недостаточно прав")


async def get_admin_by_login(db: AsyncSession, login: str) -> AdminUser | None:
    return await db.scalar(select(AdminUser).where(AdminUser.login == login))


