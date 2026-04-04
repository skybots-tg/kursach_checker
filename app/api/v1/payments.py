from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.integrations.prodamus import create_payment_link, verify_signature
from app.models import CreditsBalance, CreditsTransactionType, Order, OrderStatus, PaymentProdamus, Product, User
from app.services.credits import add_credits

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

    payment_url = await create_payment_link(
        order_id=str(order.id),
        amount=float(product.price),
        product_name=product.name,
    )
    if not payment_url:
        raise HTTPException(status_code=502, detail="Не удалось создать ссылку на оплату")

    payment = PaymentProdamus(
        order_id=order.id,
        status="created",
        raw_payload={"payment_url": payment_url},
    )
    db.add(payment)
    await db.commit()

    return {
        "order_id": order.id,
        "payment_url": payment_url,
        "product_id": payload.product_id,
        "status": "created",
    }


@router.post("/webhook/prodamus")
async def prodamus_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    content_type = request.headers.get("content-type", "")
    if "json" in content_type:
        body = await request.json()
    else:
        form = await request.form()
        body = {k: str(v) for k, v in form.items()}

    signature = request.headers.get("Sign", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    verify_data = {k: v for k, v in body.items() if k != "signature"}
    if not verify_signature(verify_data, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = body

    order_ref = payload.get("order_num") or payload.get("order_id")
    if not order_ref:
        return {"message": "ignored", "reason": "missing_order_id"}

    try:
        order_id = int(str(order_ref))
    except ValueError:
        return {"message": "ignored", "reason": "invalid_order_id"}

    order = await db.get(Order, order_id)
    if not order:
        return {"message": "ignored", "reason": "order_not_found"}

    payment_status = str(payload.get("payment_status") or payload.get("status") or "").lower()
    invoice_id = str(payload.get("payment_id") or payload.get("invoice_id") or "")

    payment = await db.scalar(select(PaymentProdamus).where(PaymentProdamus.order_id == order.id))
    if not payment:
        payment = PaymentProdamus(order_id=order.id, status="created", raw_payload={})
        db.add(payment)

    payment.raw_payload = payload
    payment.status = payment_status or payment.status
    if invoice_id:
        payment.prodamus_invoice_id = invoice_id

    if payment_status not in {"success", "paid"}:
        await db.commit()
        return {"message": "ignored", "reason": "status_not_success", "status": payment_status}

    if order.status == OrderStatus.paid:
        await db.commit()
        return {"message": "already_processed", "order_id": order.id}

    order.status = OrderStatus.paid
    order.paid_at = datetime.utcnow()

    product = await db.get(Product, order.product_id)
    credits_amount = int(product.credits_amount if product else 1)

    await add_credits(
        db,
        user_id=order.user_id,
        amount=credits_amount,
        tx_type=CreditsTransactionType.topup,
        description=f"Payment for order #{order.id}" + (f" ({product.name})" if product else ""),
        reference_type="order",
        reference_id=order.id,
    )

    await db.commit()
    return {"message": "processed", "order_id": order.id, "order_status": order.status.value}
