from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.session import engine
from app.models import Product


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_defaults(session: AsyncSession) -> None:
    exists = await session.scalar(select(Product.id).limit(1))
    if exists:
        return

    session.add(
        Product(
            name="Кредит 1 проверка",
            price=499,
            currency="RUB",
            credits_amount=1,
            active=True,
        )
    )
    await session.commit()

