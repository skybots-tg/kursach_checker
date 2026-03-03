from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import create_admin_token, get_admin_by_login, get_current_admin, require_role
from app.db.session import get_db
from app.models import AdminUser, AuditLog, Check, Order, OrderStatus

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminLoginRequest(BaseModel):
    login: str
    password: str


class AdminCreateRequest(BaseModel):
    login: str
    password: str
    role: str = "admin"


@router.post("/auth/login")
async def admin_login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    admin = await get_admin_by_login(db, payload.login)
    if not admin or not pwd_context.verify(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Неверные учётные данные")
    token = create_admin_token(admin.id, admin.role)
    return {"access_token": token, "token_type": "bearer", "role": admin.role}


@router.post("/users")
async def create_admin_user(
    payload: AdminCreateRequest,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    require_role(current_admin, {"owner"})
    exists = await get_admin_by_login(db, payload.login)
    if exists:
        raise HTTPException(status_code=409, detail="Логин уже занят")

    item = AdminUser(
        login=payload.login,
        password_hash=pwd_context.hash(payload.password),
        role=payload.role,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": item.id, "login": item.login, "role": item.role}


@router.get("/dashboard")
async def dashboard(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    now = datetime.utcnow()
    since_7d = now - timedelta(days=7)
    since_day = now - timedelta(days=1)

    checks_today = await db.scalar(select(func.count(Check.id)).where(Check.created_at >= since_day))
    checks_7d = await db.scalar(select(func.count(Check.id)).where(Check.created_at >= since_7d))
    payments_today = await db.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.paid, Order.created_at >= since_day)
    )
    payments_7d = await db.scalar(
        select(func.count(Order.id)).where(Order.status == OrderStatus.paid, Order.created_at >= since_7d)
    )

    events = await db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(20))
    return {
        "kpi": {
            "checks_today": int(checks_today or 0),
            "checks_7d": int(checks_7d or 0),
            "payments_today": int(payments_today or 0),
            "payments_7d": int(payments_7d or 0),
        },
        "events": [
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }
