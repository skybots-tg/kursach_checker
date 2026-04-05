from __future__ import annotations

import re
from pathlib import Path

from app.rules_engine.docx_snapshot import DocumentSnapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.rules_config import RulesConfig


def run_heading_formatting_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("heading_formatting"):
        return

    severity = cfg.severity("heading_formatting", "warning")
    params = cfg.params("heading_formatting")

    expected_font = str(params.get("font", "Times New Roman")).lower()
    expected_size = float(params.get("size_pt", 14))
    require_bold = bool(params.get("require_bold", True))
    level1_alignment = str(params.get("level1_alignment", "CENTER")).upper()

    for h in snapshot.heading_snapshots:
        loc = f"заголовок «{h.text[:40]}»"

        if h.font_name and h.font_name.lower() != expected_font:
            add_finding(
                findings,
                title="Шрифт заголовка",
                category="heading_formatting",
                severity=severity,
                expected=params.get("font", "Times New Roman"),
                found=h.font_name,
                location=loc,
                recommendation="Приведите шрифт заголовка к требуемому",
            )

        if h.font_size_pt and abs(h.font_size_pt - expected_size) > 0.5:
            add_finding(
                findings,
                title="Размер шрифта заголовка",
                category="heading_formatting",
                severity=severity,
                expected=f"{expected_size} pt",
                found=f"{h.font_size_pt} pt",
                location=loc,
                recommendation="Установите корректный размер шрифта для заголовка",
            )

        if require_bold and h.bold is False:
            add_finding(
                findings,
                title="Выделение заголовка",
                category="heading_formatting",
                severity=severity,
                expected="Полужирное начертание",
                found="Обычное начертание",
                location=loc,
                recommendation="Выделите заголовок полужирным шрифтом",
            )

        if h.level == 1 and h.alignment:
            if level1_alignment == "CENTER" and "CENTER" not in h.alignment.upper():
                add_finding(
                    findings,
                    title="Выравнивание заголовка 1-го уровня",
                    category="heading_formatting",
                    severity=severity,
                    expected="По центру",
                    found=h.alignment,
                    location=loc,
                    recommendation="Выровняйте заголовки первого уровня по центру",
                )


def run_page_numbering_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("page_numbering"):
        return

    severity = cfg.severity("page_numbering", "warning")
    params = cfg.params("page_numbering")

    if bool(params.get("require", True)) and not snapshot.has_page_numbers:
        add_finding(
            findings,
            title="Нумерация страниц",
            category="page_numbering",
            severity=severity,
            expected="Нумерация страниц присутствует",
            found="Нумерация страниц не обнаружена",
            location="колонтитулы",
            recommendation="Добавьте нумерацию страниц в нижний колонтитул",
        )


def run_toc_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("toc"):
        return

    severity = cfg.severity("toc", "warning")
    params = cfg.params("toc")

    if bool(params.get("require", True)) and not snapshot.has_toc:
        add_finding(
            findings,
            title="Оглавление",
            category="toc",
            severity=severity,
            expected="Автоматическое оглавление присутствует",
            found="Оглавление не обнаружено",
            location="структура",
            recommendation="Добавьте автоматическое оглавление (поле TOC) в документ",
        )


def run_footnotes_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("footnotes"):
        return

    severity = cfg.severity("footnotes", "warning")
    params = cfg.params("footnotes")

    if params.get("required", False) and snapshot.footnotes_count == 0:
        add_finding(
            findings,
            title="Сноски",
            category="footnotes",
            severity=severity,
            expected="В документе есть сноски",
            found="Сноски отсутствуют",
            location="документ",
            recommendation="Добавьте сноски при необходимости",
        )

    min_count = int(params.get("min_count", 0))
    if min_count > 0 and snapshot.footnotes_count < min_count:
        add_finding(
            findings,
            title="Количество сносок",
            category="footnotes",
            severity=severity,
            expected=f"Не менее {min_count}",
            found=str(snapshot.footnotes_count),
            location="документ",
            recommendation="Добавьте недостающие сноски",
        )


def run_captions_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("captions"):
        return

    severity = cfg.severity("captions", "warning")
    params = cfg.params("captions")

    figure_pattern = str(params.get("figure_pattern", r"^Рисунок\s+\d+\s*[—–-]\s*\S"))
    table_pattern = str(params.get("table_pattern", r"^Таблица\s+\d+\s*[—–-]\s*\S"))

    figures = [c for c in snapshot.captions if c.caption_type == "figure"]
    tables = [c for c in snapshot.captions if c.caption_type == "table"]

    for fig in figures:
        if not re.match(figure_pattern, fig.text):
            add_finding(
                findings,
                title="Формат подписи рисунка",
                category="captions",
                severity=severity,
                expected="Рисунок N — Название",
                found=fig.text[:60],
                location=f"абзац #{fig.index + 1}",
                recommendation="Оформите подпись: «Рисунок N — Название»",
            )

    for tbl in tables:
        if not re.match(table_pattern, tbl.text):
            add_finding(
                findings,
                title="Формат подписи таблицы",
                category="captions",
                severity=severity,
                expected="Таблица N — Название",
                found=tbl.text[:60],
                location=f"абзац #{tbl.index + 1}",
                recommendation="Оформите подпись: «Таблица N — Название»",
            )

    if params.get("check_sequential_numbering", True):
        _check_sequential(figures, "Рисунок", findings, severity)
        _check_sequential(tables, "Таблица", findings, severity)


def _check_sequential(
    captions: list, label: str, findings: list[Finding], severity: str,
) -> None:
    numbers = [c.number for c in captions if c.number is not None]
    if not numbers:
        return
    expected_seq = list(range(1, len(numbers) + 1))
    if numbers != expected_seq:
        add_finding(
            findings,
            title=f"Последовательная нумерация: {label}",
            category="captions",
            severity=severity,
            expected=f"Последовательная нумерация 1…{len(numbers)}",
            found=f"Нумерация: {', '.join(str(n) for n in numbers[:10])}",
            location="объекты",
            recommendation=f"Проверьте последовательность нумерации «{label}»",
        )


# ── bibliography & objects (перенесены из checks_core) ──────────────

_BIBLIOGRAPHY_MARKERS = [
    "список литературы",
    "список использованных источников и литературы",
    "список использованных источников",
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

    refs = re.findall(r"(?m)^\s*(?:\[?\d{1,3}\]?)[\.)]\s+.+$", bib_section)
    found_count = len(refs)
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

    if params.get("forbid_linked_media", True) and b'TargetMode="External"' in raw:
        add_finding(
            findings,
            title="Связанные внешние объекты",
            category="objects",
            severity=severity,
            expected="Таблицы и изображения встроены в документ",
            found="Обнаружены внешние ссылки на объекты",
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
