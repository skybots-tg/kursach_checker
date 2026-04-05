from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Order, OrderStatus, Product, User

router = APIRouter()


@router.get("")
async def list_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.execute(
        select(Order, Product)
        .join(Product, Product.id == Order.product_id)
        .where(Order.user_id == current_user.id)
        .order_by(Order.id.desc())
    )
    return [
        {
            "id": o.id,
            "amount": float(o.amount),
            "status": getattr(o.status, 'value', o.status),
            "product": p.name,
            "created_at": o.created_at,
            "paid_at": o.paid_at,
        }
        for o, p in rows
    ]


@router.get("/{order_id}/status")
async def get_order_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await db.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    result: dict = {
        "order_id": order.id,
        "status": getattr(order.status, "value", order.status),
    }

    if order.status == OrderStatus.paid:
        product = await db.get(Product, order.product_id)
        result["credits_added"] = int(product.credits_amount) if product else 0

    return result
