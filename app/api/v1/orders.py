from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Order, Product, User

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
            "status": o.status.value,
            "product": p.name,
            "created_at": o.created_at,
            "paid_at": o.paid_at,
        }
        for o, p in rows
    ]
