from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, Check, SystemSetting
from app.schemas.admin_autofix import (
    AUTOFIX_RULES_CATALOG,
    NOT_AUTOFIXABLE_INFO,
    AutofixDefaultsIn,
    AutofixGlobalConfig,
    AutofixRuleInfo,
    AutofixSafetyLimits,
    AutofixStatsOut,
)
from app.services.audit import log_admin_action

router = APIRouter()

SETTINGS_KEY = "autofix_global"


async def _load_config(db: AsyncSession) -> AutofixGlobalConfig:
    row = await db.get(SystemSetting, SETTINGS_KEY)
    if row is None:
        return AutofixGlobalConfig()
    return AutofixGlobalConfig.model_validate(row.value)


async def _save_config(
    db: AsyncSession, config: AutofixGlobalConfig, admin: AdminUser,
) -> None:
    row = await db.get(SystemSetting, SETTINGS_KEY)
    payload = config.model_dump()
    if row is None:
        row = SystemSetting(
            key=SETTINGS_KEY,
            value=payload,
            updated_at=datetime.utcnow(),
            updated_by_admin_id=admin.id,
        )
        db.add(row)
    else:
        row.value = payload
        row.updated_at = datetime.utcnow()
        row.updated_by_admin_id = admin.id

    await log_admin_action(db, admin.id, "update", "system_settings", SETTINGS_KEY, payload)
    await db.commit()


@router.get("/rules", summary="Каталог типов автоисправлений")
async def list_autofix_rules(
    _admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return {
        "fixable": [r.model_dump() for r in AUTOFIX_RULES_CATALOG],
        "not_fixable": [r.model_dump() for r in NOT_AUTOFIXABLE_INFO],
    }


@router.get("/config", summary="Глобальная конфигурация автоисправлений")
async def get_autofix_config(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    config = await _load_config(db)
    return config.model_dump()


@router.put("/config/defaults", summary="Обновить дефолты автоисправлений")
async def update_autofix_defaults(
    body: AutofixDefaultsIn,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    config = await _load_config(db)
    config.defaults = body
    await _save_config(db, config, admin)
    return {"ok": True, "config": config.model_dump()}


@router.put("/config/safety", summary="Обновить пределы безопасности")
async def update_autofix_safety(
    body: AutofixSafetyLimits,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    config = await _load_config(db)
    config.safety_limits = body
    await _save_config(db, config, admin)
    return {"ok": True, "config": config.model_dump()}


@router.get("/stats", summary="Статистика автоисправлений")
async def get_autofix_stats(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AutofixStatsOut:
    total_with_fix = await db.scalar(
        select(func.count()).select_from(Check).where(Check.output_file_id.isnot(None))
    ) or 0

    total_checks = await db.scalar(select(func.count()).select_from(Check)) or 0
    avg = round(total_with_fix / max(total_checks, 1), 2)

    return AutofixStatsOut(
        total_checks_with_autofix=total_with_fix,
        total_autofixed_items=total_with_fix,
        avg_fixes_per_check=avg,
    )
