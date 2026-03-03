from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import validate_prodamus_signature
from app.db.session import get_db
from app.integrations.prodamus import build_payment_url
from app.models import CreditsBalance, Order, OrderStatus, PaymentProdamus, Product, User

router = APIRouter()


class PaymentCreateRequest(BaseModel):
    product_id: int


@router.post("/create")
async def create_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    product = await db.get(Product, payload.product_id)
    if not product or not product.active:
        raise HTTPException(status_code=404, detail="Продукт не найден")

    order = Order(
        user_id=current_user.id,
        product_id=product.id,
        status=OrderStatus.created,
        amount=product.price,
    )
    db.add(order)
    await db.flush()

    payment = PaymentProdamus(order_id=order.id, status="created", raw_payload={})
    db.add(payment)
    await db.commit()

    payment_url = build_payment_url(order.id, float(product.price), current_user.id)
    return {"order_id": order.id, "payment_url": payment_url, "product_id": payload.product_id}


@router.post("/webhook/prodamus")
async def prodamus_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: str | None = Header(default=None),
) -> dict:
    raw = await request.body()
    if not validate_prodamus_signature(raw, x_signature, settings.prodamus_secret_key):
        raise HTTPException(status_code=401, detail="Некорректная подпись Prodamus")

    payload = await request.json()
    order_id = int(payload.get("order_id", 0))
    status = str(payload.get("status", "")).lower()
    invoice_id = str(payload.get("invoice_id", ""))

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    payment = await db.scalar(select(PaymentProdamus).where(PaymentProdamus.order_id == order.id))
    if not payment:
        payment = PaymentProdamus(order_id=order.id, status="created", raw_payload={})
        db.add(payment)

    payment.prodamus_invoice_id = invoice_id or payment.prodamus_invoice_id
    payment.raw_payload = payload
    payment.status = status or payment.status

    if status == "paid" and order.status != OrderStatus.paid:
        order.status = OrderStatus.paid
        order.paid_at = datetime.utcnow()

        product = await db.get(Product, order.product_id)
        credits = await db.get(CreditsBalance, order.user_id)
        if not credits:
            credits = CreditsBalance(user_id=order.user_id, credits_available=0)
            db.add(credits)
            await db.flush()

        credits.credits_available += int(product.credits_amount if product else 1)
        credits.updated_at = datetime.utcnow()

    await db.commit()
    return {"message": "Webhook обработан", "order_id": order.id, "order_status": order.status.value}
