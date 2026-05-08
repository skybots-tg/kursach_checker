from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Order, PaymentProdamus, Product, User

router = APIRouter()


class OrderStatusIn(BaseModel):
    status: str


@router.get("")
async def list_orders(
    status: str | None = None,
    period: str | None = None,
    source: str | None = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin

    prodamus_exists = exists(
        select(PaymentProdamus.id).where(PaymentProdamus.order_id == Order.id)
    ).correlate(Order)

    stmt = (
        select(Order, User, Product, prodamus_exists.label("has_prodamus"))
        .join(User, User.id == Order.user_id)
        .join(Product, Product.id == Order.product_id)
        .order_by(Order.id.desc())
    )

    if status:
        stmt = stmt.where(Order.status == status)

    if period == "day":
        since = datetime.utcnow() - timedelta(days=1)
        stmt = stmt.where(Order.created_at >= since)
    elif period == "week":
        since = datetime.utcnow() - timedelta(weeks=1)
        stmt = stmt.where(Order.created_at >= since)
    elif period == "month":
        since = datetime.utcnow() - timedelta(days=30)
        stmt = stmt.where(Order.created_at >= since)

    if source == "prodamus":
        stmt = stmt.where(prodamus_exists)
    elif source == "other":
        stmt = stmt.where(~prodamus_exists)

    rows = (await db.execute(stmt)).all()

    items = []
    total_sum = 0.0
    paid_sum = 0.0
    for o, u, p, has_prod in rows:
        amt = float(o.amount)
        total_sum += amt
        st = o.status.value if hasattr(o.status, "value") else o.status
        if st == "paid":
            paid_sum += amt
        items.append({
            "id": o.id,
            "status": st,
            "amount": amt,
            "has_prodamus": has_prod,
            "user": {"id": u.id, "telegram_id": u.telegram_id, "username": u.username},
            "product": {"id": p.id, "name": p.name},
            "created_at": o.created_at,
            "paid_at": o.paid_at,
        })

    return {
        "items": items,
        "total_sum": round(total_sum, 2),
        "paid_sum": round(paid_sum, 2),
        "count": len(items),
    }


@router.get("/{order_id}")
async def get_order_card(
    order_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    row = await db.execute(
        select(Order, User, Product)
        .join(User, User.id == Order.user_id)
        .join(Product, Product.id == Order.product_id)
        .where(Order.id == order_id)
    )
    data = row.first()
    if not data:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order, user, product = data
    payment_logs = await db.scalars(
        select(PaymentProdamus).where(PaymentProdamus.order_id == order_id).order_by(PaymentProdamus.id.desc())
    )
    return {
        "order": {
            "id": order.id,
            "status": order.status.value if hasattr(order.status, "value") else order.status,
            "amount": float(order.amount),
            "created_at": order.created_at,
            "paid_at": order.paid_at,
        },
        "user": {"id": user.id, "telegram_id": user.telegram_id, "username": user.username},
        "product": {"id": product.id, "name": product.name},
        "payment_logs": [
            {
                "id": p.id,
                "status": p.status,
                "invoice_id": p.prodamus_invoice_id,
                "raw_payload": p.raw_payload,
                "created_at": p.created_at,
            }
            for p in payment_logs
        ],
    }


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    payload: OrderStatusIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ = current_admin
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = payload.status
    await db.commit()
    return {"ok": True}


