"""Public products listing — active products visible to all authenticated users."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Product

router = APIRouter()


@router.get("")
async def list_products(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.id)
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "currency": p.currency,
            "credits_amount": p.credits_amount,
            "description": None,
        }
        for p in rows
    ]
