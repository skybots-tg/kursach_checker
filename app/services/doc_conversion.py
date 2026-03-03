from __future__ import annotations

import shlex
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.core.config import settings


def convert_doc_to_docx(input_path: str) -> tuple[str | None, str | None]:
    source = Path(input_path)
    if source.suffix.lower() != ".doc":
        return str(source), None

    command_template = (settings.doc_to_docx_converter or "").strip()
    if not command_template:
        return None, "DOC не поддерживается: конвертер DOC→DOCX не настроен"

    outdir = Path(tempfile.gettempdir()) / "kursach_checker" / "converted"
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        command = command_template.format(outdir=str(outdir), input=str(source))
    except KeyError:
        return None, "Некорректный шаблон команды конвертации DOC→DOCX"

    try:
        completed = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"Ошибка запуска конвертера DOC→DOCX: {exc}"

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        details = stderr or stdout or f"code={completed.returncode}"
        return None, f"Конвертация DOC→DOCX завершилась с ошибкой: {details}"

    expected = outdir / f"{source.stem}.docx"
    if expected.exists():
        target = outdir / f"{source.stem}_{uuid.uuid4().hex}.docx"
        expected.replace(target)
        return str(target), None

    variants = sorted(outdir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not variants:
        return None, "Конвертер не создал DOCX файл"

    return str(variants[0]), None

