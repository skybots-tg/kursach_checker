from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models_users import Order, Product, ProdamusPayment
from backend.services.users import UserService


class PaymentsService:
    """Работа с продуктами, заказами и платежами Prodamus."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_products(self) -> list[Product]:
        stmt = select(Product).where(Product.active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_order(self, user_id: int, product_id: int) -> Order:
        stmt = select(Product).where(Product.id == product_id, Product.active.is_(True))
        result = await self.session.execute(stmt)
        product = result.scalar_one()

        order = Order(
            user_id=user_id,
            product_id=product.id,
            status="created",
            amount=Decimal(product.price),
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def mark_payment_paid(
        self,
        order: Order,
        payment: ProdamusPayment,
        credits_amount: int,
    ) -> None:
        """
        Идемпотентно начисляет кредиты по успешному платежу.
        """
        if order.status == "paid":
            return

        order.status = "paid"
        await self.session.flush()

        user_service = UserService(self.session)
        await user_service.add_credits(order.user_id, credits_amount)






