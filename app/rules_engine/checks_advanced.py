from __future__ import annotations

import re

from app.rules_engine.docx_snapshot import DocumentSnapshot
from app.rules_engine.findings import Finding, add_finding, display_alignment
from app.rules_engine.heading_detection import (
    CHAPTER_RE,
    TOC_LINE_TAIL_RE,
    detect_heading_candidate,
)
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
                expected=f"{expected_size} \u043f\u0442",
                found=f"{h.font_size_pt} \u043f\u0442",
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
                    found=display_alignment(h.alignment),
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

    if params.get("title_page_no_number", True) and snapshot.has_page_numbers:
        if not snapshot.first_section_title_page:
            add_finding(
                findings,
                title="Нумерация титульного листа",
                category="page_numbering",
                severity=severity,
                expected="Титульный лист не нумеруется (нумерация со второй страницы)",
                found="Первая страница нумеруется наравне с остальными",
                location="первая секция документа",
                recommendation="Включите 'Особый колонтитул для первой страницы' и уберите номер с титульного листа",
            )


def run_toc_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("toc"):
        return

    severity = cfg.severity("toc", "warning")
    params = cfg.params("toc")

    if not bool(params.get("require", True)):
        return

    has_heading_candidates = any(
        detect_heading_candidate(p.text.strip()) is not None
        for p in snapshot.paragraphs
        if p.text and not p.is_toc_entry
    )

    if snapshot.has_toc:
        return

    has_manual_toc = _detect_manual_toc_content(snapshot)

    if has_manual_toc:
        add_finding(
            findings,
            title="Содержание оформлено вручную",
            category="toc",
            severity=severity,
            expected="Автоматическое оглавление (поле TOC)",
            found="Содержание набрано текстом, без поля TOC",
            location="структура",
            recommendation=(
                "Удалите ручное содержание и вставьте автоматическое оглавление "
                "на основе стилей заголовков (Ссылки → Оглавление)"
            ),
        )
    else:
        recommendation = "Добавьте автоматическое оглавление (поле TOC) в документ"
        if has_heading_candidates:
            recommendation += (
                ". Убедитесь, что заголовки размечены стилями Word «Заголовок 1/2/3»"
            )
        add_finding(
            findings,
            title="Оглавление",
            category="toc",
            severity=severity,
            expected="Автоматическое оглавление присутствует",
            found="Оглавление не обнаружено",
            location="структура",
            recommendation=recommendation,
        )


def _detect_manual_toc_content(snapshot: DocumentSnapshot) -> bool:
    """Heuristic: manual TOC = lines with page-number tails near a 'содержание' heading."""
    in_toc_zone = False
    toc_like_lines = 0
    for para in snapshot.paragraphs:
        if not para.text:
            continue
        text_lower = para.text.strip().lower()
        if text_lower in ("содержание", "оглавление"):
            in_toc_zone = True
            continue
        if in_toc_zone:
            if para.is_heading or len(para.text.strip()) > 200:
                break
            if TOC_LINE_TAIL_RE.search(para.text.strip()):
                toc_like_lines += 1
            if toc_like_lines >= 3:
                return True
    return False


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


# Backward-compatible aliases — canonical patterns live in heading_detection.py
_CHAPTER_RE = CHAPTER_RE
_TOC_LINE_TAIL_RE = TOC_LINE_TAIL_RE


def run_section_breaks_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    if not cfg.has("section_breaks"):
        return

    severity = cfg.severity("section_breaks", "warning")
    params = cfg.params("section_breaks")

    named_sections = [s.lower() for s in params.get("sections_requiring_break", [])]
    chapters_require = bool(params.get("chapters_require_break", True))

    for para in snapshot.paragraphs:
        if not para.text or para.index == 0:
            continue
        if para.is_toc_entry:
            continue
        if _TOC_LINE_TAIL_RE.search(para.text.strip()):
            continue
        if not para.is_heading and len(para.text.strip()) > 100:
            continue

        text_lower = para.text.strip().lower()
        level = para.heading_level
        needs_break = False
        match_label = ""

        for section_name in named_sections:
            if section_name in text_lower:
                needs_break = True
                match_label = para.text.strip()
                break

        if not needs_break and chapters_require:
            if (para.is_heading and level == 1) or _CHAPTER_RE.match(para.text.strip()):
                needs_break = True
                match_label = para.text.strip()

        if needs_break and not para.page_break_before:
            short = match_label[:50]
            add_finding(
                findings,
                title="Раздел не с новой страницы",
                category="section_breaks",
                severity=severity,
                expected="Раздел начинается с новой страницы",
                found=f"Раздел «{short}» продолжает предыдущую страницу",
                location=f"абзац #{para.index + 1}",
                recommendation="Вставьте разрыв страницы перед этим разделом",
            )


# ── Re-exports from checks_content (backward compatibility for autofix imports) ──

from app.rules_engine.checks_content import (  # noqa: F401, E402
    ALLOWED_CHARS_RE,
    run_bibliography_checks,
    run_objects_checks,
    run_text_cleanliness_checks,
)

_ALLOWED_CHARS_RE = ALLOWED_CHARS_RE
