"""Refresh DOCX fields via LibreOffice headless.

After autofix inserts a TOC field, this module re-saves the file through
LibreOffice so that the TOC gets real page numbers.  The fixed DOCX already
has ``<w:updateFields val="true"/>`` in ``word/settings.xml``, so LibreOffice
updates all fields on open/save.

If LibreOffice is not available the step is silently skipped — the cached
TOC entries (built from headings by ``autofix_toc``) remain as fallback.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_SOFFICE_TIMEOUT = 45


def _find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return None


def refresh_fields_via_libreoffice(
    docx_path: Path, details: list[str],
) -> bool:
    """Re-save *docx_path* through LibreOffice headless to update TOC fields.

    Returns True if the file was successfully refreshed.
    """
    soffice = _find_soffice()
    if soffice is None:
        return False

    outdir = Path(tempfile.gettempdir()) / "kursach_checker" / "lo_refresh" / uuid.uuid4().hex
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [
        soffice,
        "--headless",
        "--norestore",
        "--convert-to", "docx:MS Word 2007 XML",
        "--outdir", str(outdir),
        str(docx_path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
            timeout=_SOFFICE_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Autofix: LibreOffice field refresh failed: %s", exc)
        return False

    if result.returncode != 0:
        logger.debug(
            "Autofix: LibreOffice exited %d: %s",
            result.returncode, (result.stderr or result.stdout or "")[:200],
        )
        return False

    refreshed = outdir / docx_path.name
    if not refreshed.exists():
        for candidate in outdir.iterdir():
            if candidate.suffix.lower() == ".docx":
                refreshed = candidate
                break
        else:
            logger.debug("Autofix: LibreOffice produced no output in %s", outdir)
            return False

    try:
        shutil.copy2(str(refreshed), str(docx_path))
    except Exception:
        logger.debug("Autofix: failed to copy refreshed DOCX back to %s", docx_path)
        return False

    details.append("Оглавление: поля обновлены через LibreOffice (с номерами страниц)")
    return True
