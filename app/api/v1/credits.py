from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import CreditsTransaction, User

router = APIRouter()


@router.get("/history")
async def my_credits_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(CreditsTransaction)
        .where(CreditsTransaction.user_id == current_user.id)
        .order_by(CreditsTransaction.id.desc())
        .offset(offset)
        .limit(min(limit, 200))
    )
    rows = await db.scalars(stmt)
    return [
        {
            "id": t.id,
            "tx_type": t.tx_type,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "description": t.description,
            "created_at": t.created_at,
        }
        for t in rows
    ]
