from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Product
from app.services.audit import log_admin_action

router = APIRouter()


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)
    currency: str = Field(default="RUB", min_length=1, max_length=10)
    credits_amount: int = Field(default=1, ge=1)
    active: bool = True


@router.get("")
async def list_products(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    _ = current_admin
    rows = await db.scalars(select(Product).order_by(Product.id.desc()))
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "currency": p.currency,
            "credits_amount": p.credits_amount,
            "active": p.active,
        }
        for p in rows
    ]


@router.post("")
async def create_product(
    payload: ProductIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = Product(**payload.model_dump())
    db.add(item)
    await db.flush()

    await log_admin_action(
        db,
        current_admin.id,
        "product.create",
        "product",
        str(item.id),
        {"after": payload.model_dump()},
    )
    await db.commit()
    return {"id": item.id}


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    payload: ProductIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    before = {
        "name": item.name,
        "price": float(item.price),
        "currency": item.currency,
        "credits_amount": item.credits_amount,
        "active": item.active,
    }
    for k, v in payload.model_dump().items():
        setattr(item, k, v)

    await log_admin_action(
        db,
        current_admin.id,
        "product.update",
        "product",
        str(item.id),
        {"before": before, "after": payload.model_dump()},
    )
    await db.commit()
    return {"ok": True}


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await db.get(Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    await db.delete(item)
    await log_admin_action(db, current_admin.id, "product.delete", "product", str(product_id), {"deleted": True})
    await db.commit()
    return {"ok": True}

