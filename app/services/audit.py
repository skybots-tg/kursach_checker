from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_admin_action(
    db: AsyncSession,
    admin_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str,
    diff: dict,
) -> None:
    db.add(
        AuditLog(
            admin_user_id=admin_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            diff_json=diff,
            created_at=datetime.utcnow(),
        )
    )


