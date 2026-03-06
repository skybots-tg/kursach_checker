from __future__ import annotations

import shlex
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin_deps import get_current_admin
from app.db.session import get_db
from app.models import AdminUser, SystemSetting
from app.schemas.admin_settings import (
    DocConverterSettings,
    DocConverterTestResult,
    SystemSettingsOut,
)
from app.services.audit import log_admin_action

router = APIRouter()

DOC_CONVERTER_KEY = "doc_converter"


async def _load_doc_converter(db: AsyncSession) -> DocConverterSettings:
    row = await db.get(SystemSetting, DOC_CONVERTER_KEY)
    if row is None:
        return DocConverterSettings()
    return DocConverterSettings.model_validate(row.value)


async def _save_setting(
    db: AsyncSession,
    key: str,
    value: dict,
    admin: AdminUser,
) -> None:
    row = await db.get(SystemSetting, key)
    if row is None:
        row = SystemSetting(
            key=key,
            value=value,
            updated_at=datetime.utcnow(),
            updated_by_admin_id=admin.id,
        )
        db.add(row)
    else:
        row.value = value
        row.updated_at = datetime.utcnow()
        row.updated_by_admin_id = admin.id

    await log_admin_action(db, admin.id, "update", "system_settings", key, value)
    await db.commit()


@router.get("", summary="Все системные настройки")
async def get_system_settings(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    doc = await _load_doc_converter(db)
    return SystemSettingsOut(doc_converter=doc).model_dump()


@router.get("/doc-converter", summary="Настройки DOC→DOCX конвертера")
async def get_doc_converter(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cfg = await _load_doc_converter(db)
    return cfg.model_dump()


@router.put("/doc-converter", summary="Обновить настройки DOC→DOCX конвертера")
async def update_doc_converter(
    body: DocConverterSettings,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = body.model_dump()
    await _save_setting(db, DOC_CONVERTER_KEY, payload, admin)
    return {"ok": True, "doc_converter": payload}


@router.post("/doc-converter/test", summary="Проверить работоспособность DOC конвертера")
async def test_doc_converter(
    _admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DocConverterTestResult:
    cfg = await _load_doc_converter(db)

    if not cfg.enabled:
        return DocConverterTestResult(ok=False, message="Конвертер отключён в настройках")

    cmd_tpl = cfg.command_template.strip()
    if not cmd_tpl:
        return DocConverterTestResult(ok=False, message="Шаблон команды не задан")

    version = _detect_converter_version(cmd_tpl)
    if version is None:
        return DocConverterTestResult(
            ok=False,
            message="Не удалось определить версию конвертера. Проверьте, что программа установлена и доступна в PATH",
        )

    return DocConverterTestResult(
        ok=True,
        message="Конвертер доступен и готов к работе",
        converter_version=version,
    )


def _detect_converter_version(cmd_template: str) -> str | None:
    executable = shlex.split(cmd_template)[0] if cmd_template else ""
    if not executable:
        return None

    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        output = (result.stdout or "").strip() or (result.stderr or "").strip()
        first_line = output.split("\n")[0] if output else ""
        return first_line or None
    except Exception:  # noqa: BLE001
        return None
