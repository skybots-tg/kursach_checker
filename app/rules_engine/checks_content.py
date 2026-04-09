"""Content quality checks: bibliography, embedded objects, text cleanliness.

Split from checks_advanced.py to respect the 500-line file limit.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.rules_engine.docx_snapshot import DocumentSnapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.rules_config import RulesConfig

# ── bibliography ─────────────────────────────────────────────────────

_BIBLIOGRAPHY_MARKERS = [
    "список литературы",
    "список использованных источников и литературы",
    "список использованных источников",
    "библиографический список",
    "list of references",
]


def _extract_bibliography_section(full_text: str) -> str | None:
    """Return text from the bibliography heading to the next heading or end."""
    lower = full_text.lower()
    best_pos = -1
    for marker in _BIBLIOGRAPHY_MARKERS:
        pos = lower.find(marker)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
    if best_pos == -1:
        return None
    section_text = full_text[best_pos:]
    lines = section_text.split("\n")
    result_lines = [lines[0]]
    for line in lines[1:]:
        stripped = line.strip()
        if stripped and stripped == stripped.upper() and len(stripped) > 3 and not re.match(r"^\s*[\[\d]", stripped):
            break
        result_lines.append(line)
    return "\n".join(result_lines)


def _count_bibliography_entries(bib_section: str) -> int:
    """Count bibliography entries by non-empty lines that look like source descriptions."""
    lines = bib_section.strip().splitlines()
    count = 0
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        if stripped == stripped.upper() and len(stripped) > 3:
            break
        count += 1
    return count


def run_bibliography_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("bibliography"):
        return

    severity = cfg.severity("bibliography", "warning")
    params = cfg.params("bibliography")
    min_total = int(params.get("min_total_sources", 20))

    bib_section = _extract_bibliography_section(snapshot.full_text)
    if bib_section is None:
        add_finding(
            findings,
            title="Раздел источников",
            category="bibliography",
            severity=severity,
            expected="В документе присутствует раздел со списком источников",
            found="Не найден",
            location="структура",
            recommendation="Добавьте раздел со списком литературы",
        )
        return

    refs_numbered = re.findall(r"(?m)^\s*(?:\[?\d{1,3}\]?)[\.)]\s+.+$", bib_section)
    refs_plain = _count_bibliography_entries(bib_section) if not refs_numbered else 0
    found_count = len(refs_numbered) or refs_plain
    if found_count < min_total:
        add_finding(
            findings,
            title="Количество источников",
            category="bibliography",
            severity=severity,
            expected=f"Не менее {min_total}",
            found=str(found_count),
            location="список литературы",
            recommendation="Добавьте недостающие источники в список литературы",
        )

    refs = refs_numbered or bib_section.strip().splitlines()[1:]
    if params.get("require_foreign_sources", False) and refs:
        latin_refs = sum(1 for r in refs if re.search(r"[A-Za-z]{3,}", r))
        if latin_refs == 0:
            add_finding(
                findings,
                title="Иноязычные источники",
                category="bibliography",
                severity=severity,
                expected="Наличие иноязычных источников",
                found="Иноязычные источники не обнаружены",
                location="список литературы",
                recommendation="Добавьте иноязычные источники в список литературы",
            )


# ── objects ───────────────────────────────────────────────────────────

def run_objects_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("objects"):
        return
    if Path(snapshot.path).suffix.lower() != ".docx":
        return

    severity = cfg.severity("objects", "warning")
    params = cfg.params("objects")

    try:
        raw = Path(snapshot.path).read_bytes()
    except OSError:
        return

    if params.get("forbid_linked_media", True):
        has_linked_media = (
            b'TargetMode="External"' in raw
            and (b"<wp:inline" in raw or b"<wp:anchor" in raw or b"oleObject" in raw.lower())
        )
        if has_linked_media:
            add_finding(
                findings,
                title="Связанные внешние объекты",
                category="objects",
                severity=severity,
                expected="Таблицы и изображения встроены в документ",
                found="Обнаружены внешние ссылки на медиа-объекты",
                location="объекты",
                recommendation="Вставьте объекты в документ как встроенные",
            )

    if params.get("require_embedded_objects", False):
        has_media = b"word/media/" in raw or b"<wp:inline" in raw or b"<wp:anchor" in raw
        if not has_media:
            add_finding(
                findings,
                title="Встроенные объекты",
                category="objects",
                severity="advice",
                expected="В документе есть рисунки или таблицы",
                found="Встроенные объекты не обнаружены",
                location="объекты",
                recommendation="Добавьте иллюстрации или таблицы в документ",
            )


# ── text cleanliness ─────────────────────────────────────────────────

ALLOWED_CHARS_RE = re.compile(
    r"[\u0000-\u007F"
    r"\u0400-\u04FF"
    r"\u00A0-\u00FF"
    r"\u0370-\u03FF"
    r"\u2010-\u2015"
    r"\u2018\u2019\u201C\u201D\u00AB\u00BB\u2026"
    r"\u2116\u0301"
    r"\u2022\u25CF\u25CB\u25A0\u25AA\u2023"
    r"\u2070-\u209F"
    r"\u2200-\u22FF"
    r"\u2150-\u218F"
    r"]"
)

_MAX_CLEANLINESS_FINDINGS = 10


def run_text_cleanliness_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("text_cleanliness"):
        return

    severity = cfg.severity("text_cleanliness", "warning")
    count = 0

    for paragraph in snapshot.paragraphs:
        if not paragraph.text or paragraph.is_toc_entry:
            continue
        if count >= _MAX_CLEANLINESS_FINDINGS:
            break
        odd_chars: list[str] = []
        for ch in paragraph.text:
            if not ALLOWED_CHARS_RE.match(ch):
                odd_chars.append(ch)
        if odd_chars:
            unique = sorted(set(odd_chars))
            sample = ", ".join(f"U+{ord(c):04X}" for c in unique[:5])
            count += 1
            add_finding(
                findings,
                title="Посторонние символы",
                category="text_cleanliness",
                severity=severity,
                expected="Текст содержит только стандартные символы",
                found=f"Обнаружены символы: {sample}",
                location=f"абзац #{paragraph.index + 1}",
                recommendation="Удалите или замените нестандартные символы",
            )

    if count >= _MAX_CLEANLINESS_FINDINGS:
        add_finding(
            findings,
            title="Посторонние символы — ещё замечания",
            category="text_cleanliness",
            severity="advice",
            expected="",
            found=f"Показаны первые {_MAX_CLEANLINESS_FINDINGS}, проблема массовая",
            location="весь документ",
            recommendation="Проверьте весь документ на посторонние символы",
        )
