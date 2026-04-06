from __future__ import annotations

import shlex
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.core.config import settings


def get_converter_command_and_timeout() -> tuple[str, int]:
    """Возвращает (command_template, timeout) из .env-настроек.

    Для работы с БД-настройками используйте
    get_converter_settings_from_db() + передавайте параметры явно.
    """
    return (settings.doc_to_docx_converter or "").strip(), 60


def convert_doc_to_docx(
    input_path: str,
    *,
    command_template: str | None = None,
    timeout_sec: int = 60,
) -> tuple[str | None, str | None]:
    source = Path(input_path)
    if source.suffix.lower() != ".doc":
        return str(source), None

    if command_template is None:
        command_template, timeout_sec = get_converter_command_and_timeout()

    command_template = (command_template or "").strip()
    if not command_template:
        return None, "DOC не поддерживается: конвертер DOC→DOCX не настроен"

    outdir = Path(tempfile.gettempdir()) / "kursach_checker" / "converted" / uuid.uuid4().hex
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        command = command_template.format(outdir=str(outdir), input=str(source))
    except KeyError:
        return None, "Invalid DOC->DOCX command template"

    try:
        completed = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_sec,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"DOC->DOCX converter launch error: {exc}"

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        details = stderr or stdout or f"code={completed.returncode}"
        return None, f"DOC->DOCX conversion failed: {details}"

    expected = outdir / f"{source.stem}.docx"
    if not expected.exists():
        return None, "Converter did not produce expected DOCX file"

    return str(expected), None


async def get_converter_settings_from_db() -> tuple[str, int, bool]:
    """Загружает настройки конвертера из БД (system_settings).

    Возвращает (command_template, timeout_sec, enabled).
    Если записи нет — фолбэк на .env.
    """
    from app.db.session import SessionLocal
    from app.models import SystemSetting

    async with SessionLocal() as db:
        row = await db.get(SystemSetting, "doc_converter")

    if row is None:
        env_cmd = (settings.doc_to_docx_converter or "").strip()
        return env_cmd, 60, bool(env_cmd)

    val = row.value or {}
    enabled = bool(val.get("enabled", False))
    cmd = str(val.get("command_template", "")).strip()
    timeout = int(val.get("timeout_sec", 60))

    if not cmd:
        env_cmd = (settings.doc_to_docx_converter or "").strip()
        return env_cmd, timeout, enabled and bool(env_cmd)

    return cmd, timeout, enabled


