from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreditsBalance, CreditsTransaction, CreditsTransactionType


async def _ensure_balance(db: AsyncSession, user_id: int) -> CreditsBalance:
    balance = await db.get(CreditsBalance, user_id)
    if not balance:
        balance = CreditsBalance(user_id=user_id, credits_available=0)
        db.add(balance)
        await db.flush()
    return balance


async def add_credits(
    db: AsyncSession,
    user_id: int,
    amount: int,
    tx_type: CreditsTransactionType,
    *,
    description: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> CreditsBalance:
    """Add credits to user balance and record a transaction."""
    balance = await _ensure_balance(db, user_id)
    balance.credits_available += amount
    balance.updated_at = datetime.utcnow()

    tx = CreditsTransaction(
        user_id=user_id,
        tx_type=tx_type.value,
        amount=amount,
        balance_after=balance.credits_available,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(tx)
    return balance


async def spend_credits(
    db: AsyncSession,
    user_id: int,
    amount: int = 1,
    *,
    description: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> CreditsBalance:
    """Deduct credits from user balance and record a transaction."""
    balance = await _ensure_balance(db, user_id)
    balance.credits_available -= amount
    balance.updated_at = datetime.utcnow()

    tx = CreditsTransaction(
        user_id=user_id,
        tx_type=CreditsTransactionType.spend.value,
        amount=-amount,
        balance_after=balance.credits_available,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(tx)
    return balance


async def set_credits(
    db: AsyncSession,
    user_id: int,
    new_value: int,
    *,
    description: str | None = None,
    admin_user_id: int | None = None,
) -> CreditsBalance:
    """Set user credits to an absolute value and record a transaction."""
    balance = await _ensure_balance(db, user_id)
    old_value = balance.credits_available
    delta = new_value - old_value

    balance.credits_available = new_value
    balance.updated_at = datetime.utcnow()

    tx = CreditsTransaction(
        user_id=user_id,
        tx_type=CreditsTransactionType.admin_set.value,
        amount=delta,
        balance_after=new_value,
        description=description or f"Admin set credits: {old_value} → {new_value}",
        reference_type="admin_user" if admin_user_id else None,
        reference_id=admin_user_id,
    )
    db.add(tx)
    return balance
