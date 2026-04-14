"""Content quality checks: bibliography, embedded objects, text cleanliness, list formatting.

Split from checks_advanced.py to respect the 500-line file limit.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.rules_engine.docx_snapshot import DocumentSnapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.rules_config import RulesConfig

_DEFAULT_INFORMAL_MARKERS = frozenset("·•*-—–")

_ENUM_LETTER_RE = re.compile(r"^[а-яёa-z]\)\s", re.IGNORECASE)
_ENUM_DIGIT_PAREN_RE = re.compile(r"^\d{1,2}\)\s")

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


_NUM_PREFIX_RE = re.compile(r"^\s*(?:\[?\d{1,3}\]?)[\.)]\s*")


def _strip_number_prefix(line: str) -> str:
    return _NUM_PREFIX_RE.sub("", line).strip()


def _sort_key(text: str) -> str:
    """Lowercase key for alphabetical comparison (Russian then Latin)."""
    return _strip_number_prefix(text).lower()


def _check_bibliography_alphabetical_order(
    bib_section: str,
    refs_numbered: list[str],
    findings: list[Finding],
    severity: str,
) -> None:
    entries = refs_numbered if refs_numbered else [
        line for line in bib_section.strip().splitlines()[1:]
        if line.strip() and len(line.strip()) >= 10
    ]
    if len(entries) < 2:
        return

    keys = [_sort_key(e) for e in entries]
    out_of_order: list[int] = []
    for i in range(1, len(keys)):
        if keys[i] < keys[i - 1]:
            out_of_order.append(i + 1)

    if out_of_order:
        sample = ", ".join(str(n) for n in out_of_order[:5])
        add_finding(
            findings,
            title="Алфавитный порядок источников",
            category="bibliography",
            severity=severity,
            expected="Источники расположены в алфавитном порядке",
            found=f"Нарушен порядок у источников № {sample}",
            location="список литературы",
            recommendation="Отсортируйте источники по алфавиту и перенумеруйте",
        )


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

    if not refs_numbered:
        add_finding(
            findings,
            title="Нумерация источников",
            category="bibliography",
            severity=severity,
            expected="Источники пронумерованы (1. 2. 3. или [1] [2] [3])",
            found="Нумерация источников не обнаружена",
            location="список литературы",
            recommendation="Пронумеруйте каждый источник по порядку: 1. 2. 3. и т.д.",
        )

    _check_bibliography_alphabetical_order(bib_section, refs_numbered, findings, severity)

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

    em_count = 0
    for paragraph in snapshot.paragraphs:
        if not paragraph.text or paragraph.is_toc_entry or paragraph.is_heading:
            continue
        if em_count >= _MAX_CLEANLINESS_FINDINGS:
            break
        if "\u2014" in paragraph.text:
            em_count += 1
            add_finding(
                findings,
                title="Длинное тире (\u2014)",
                category="text_cleanliness",
                severity=severity,
                expected="Среднее тире (\u2013) вместо длинного (\u2014)",
                found="Обнаружено длинное тире (\u2014) \u2014 признак ИИ-генерации",
                location=f"абзац #{paragraph.index + 1}",
                recommendation="Замените длинное тире (\u2014) на среднее (\u2013)",
            )
    if em_count >= _MAX_CLEANLINESS_FINDINGS:
        add_finding(
            findings,
            title="Длинное тире \u2014 ещё замечания",
            category="text_cleanliness",
            severity="advice",
            expected="",
            found=f"Показаны первые {_MAX_CLEANLINESS_FINDINGS}, проблема массовая",
            location="весь документ",
            recommendation="Замените все длинные тире (\u2014) на средние (\u2013)",
        )

    ws_count = 0
    for paragraph in snapshot.paragraphs:
        if not paragraph.text or paragraph.is_toc_entry or paragraph.is_heading:
            continue
        if ws_count >= _MAX_CLEANLINESS_FINDINGS:
            break
        if paragraph.has_leading_whitespace:
            ws_count += 1
            add_finding(
                findings,
                title="Ведущие пробелы в абзаце",
                category="text_cleanliness",
                severity=severity,
                expected="Текст без лидирующих пробелов (используйте программный отступ)",
                found="Пробелы/неразрывные пробелы в начале абзаца",
                location=f"абзац #{paragraph.index + 1}",
                recommendation="Удалите пробелы в начале и настройте отступ через Формат → Абзац",
            )
    if ws_count >= _MAX_CLEANLINESS_FINDINGS:
        add_finding(
            findings,
            title="Ведущие пробелы — ещё замечания",
            category="text_cleanliness",
            severity="advice",
            expected="",
            found=f"Показаны первые {_MAX_CLEANLINESS_FINDINGS}, проблема массовая",
            location="весь документ",
            recommendation="Проверьте все абзацы на ведущие пробелы",
        )


# ── list formatting ──────────────────────────────────────────────────

_MAX_LIST_FINDINGS = 5


def _starts_with_informal_marker(text: str, markers: frozenset[str]) -> bool:
    stripped = text.lstrip()
    if not stripped or len(stripped) < 2:
        return False
    ch = stripped[0]
    if ch not in markers:
        return False
    if ch in ("-", "\u2013", "\u2014") and stripped[1].isdigit():
        return False
    return True


def _starts_with_enumeration(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped or len(stripped) < 3:
        return False
    return bool(_ENUM_LETTER_RE.match(stripped) or _ENUM_DIGIT_PAREN_RE.match(stripped))


def run_list_formatting_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("list_formatting"):
        return

    severity = cfg.severity("list_formatting", "warning")
    params = cfg.params("list_formatting")

    markers_raw = params.get("informal_list_markers", ["\u00b7", "\u2022", "*", "-", "\u2014", "\u2013"])
    markers = frozenset(markers_raw) | _DEFAULT_INFORMAL_MARKERS
    min_consecutive = int(params.get("min_consecutive", 2))

    groups: list[list[int]] = []
    current: list[int] = []

    for para in snapshot.paragraphs:
        if not para.text or para.is_heading or para.is_toc_entry:
            if current:
                groups.append(current)
                current = []
            continue
        if para.has_numbering:
            if current:
                groups.append(current)
                current = []
            continue
        if _starts_with_informal_marker(para.text, markers) or _starts_with_enumeration(para.text):
            current.append(para.index)
        else:
            if current:
                groups.append(current)
                current = []

    if current:
        groups.append(current)

    count = 0
    for group in groups:
        if len(group) < min_consecutive:
            continue
        count += 1
        if count > _MAX_LIST_FINDINGS:
            add_finding(
                findings,
                title="Неоформленные списки — ещё замечания",
                category="list_formatting",
                severity="advice",
                expected="",
                found=f"Показаны первые {_MAX_LIST_FINDINGS}, проблема массовая",
                location="весь документ",
                recommendation="Проверьте весь документ на неоформленные списки",
            )
            break
        first_idx = group[0]
        para = snapshot.paragraphs[first_idx]
        preview = para.text[:50]
        add_finding(
            findings,
            title="Неоформленный список",
            category="list_formatting",
            severity=severity,
            expected="Элементы списка оформлены маркированным/нумерованным списком",
            found=f"Текст похож на список ({len(group)} элементов) без форматирования",
            location=f"абзац #{first_idx + 1}: \u00ab{preview}\u00bb",
            recommendation="Оформите перечисление в виде маркированного списка с длинным тире",
        )
