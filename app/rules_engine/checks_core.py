from __future__ import annotations

import re

from app.rules_engine.docx_snapshot import DocumentSnapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.rules_config import RulesConfig


def run_file_intake_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("file_intake"):
        return

    severity = cfg.severity("file_intake", "error")
    params = cfg.params("file_intake")
    allowed = {x.lower() for x in params.get("allowed_extensions", ["doc", "docx"]) if isinstance(x, str)}
    max_size_mb = int(params.get("max_size_mb", 20))

    ext = snapshot.extension.lstrip(".")
    if ext not in allowed:
        add_finding(
            findings,
            title="Формат файла",
            category="file",
            severity=severity,
            expected=f"Разрешены форматы: {', '.join(sorted(allowed))}",
            found=ext or "без расширения",
            location="input",
            recommendation="Загрузите файл в разрешённом формате",
        )

    max_size = max_size_mb * 1024 * 1024
    if snapshot.size > max_size:
        add_finding(
            findings,
            title="Размер файла",
            category="file",
            severity=severity,
            expected=f"Не более {max_size_mb} MB",
            found=f"{round(snapshot.size / 1024 / 1024, 2)} MB",
            location="input",
            recommendation="Сократите размер документа или загрузите сжатую версию",
        )


def run_integrity_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("integrity"):
        return

    severity = cfg.severity("integrity", "error")
    params = cfg.params("integrity")

    if params.get("forbid_password_protection", True) and snapshot.is_encrypted:
        add_finding(
            findings,
            title="Защита паролем",
            category="integrity",
            severity=severity,
            expected="Документ не защищён паролем",
            found="Документ защищён паролем",
            location="документ",
            recommendation="Снимите защиту паролем и загрузите файл заново",
        )

    if snapshot.is_corrupted:
        add_finding(
            findings,
            title="Повреждённый файл",
            category="integrity",
            severity=severity,
            expected="Документ корректно открывается",
            found="Документ повреждён или не может быть прочитан",
            location="документ",
            recommendation="Пересохраните документ в Word и загрузите заново",
        )

    if params.get("forbid_track_changes", True) and snapshot.revisions_present:
        add_finding(
            findings,
            title="Режим правок",
            category="integrity",
            severity=severity,
            expected="Исправления в режиме track changes отсутствуют",
            found="Обнаружены пометки вставок/удалений",
            location="документ",
            recommendation="Примите все исправления и отключите режим правок",
        )

    if params.get("forbid_comments", True) and snapshot.comments_count > 0:
        add_finding(
            findings,
            title="Комментарии в документе",
            category="integrity",
            severity=severity,
            expected="Комментарии отсутствуют",
            found=f"Найдено комментариев: {snapshot.comments_count}",
            location="документ",
            recommendation="Удалите комментарии перед отправкой на проверку",
        )


def run_context_extraction_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("context_extraction"):
        return

    severity = cfg.severity("context_extraction", "warning")
    params = cfg.params("context_extraction")
    text = snapshot.full_text

    if params.get("detect_course_year", True):
        pattern = params.get("course_year_regex", r"(?i)\b([2-6])\s*курс\b")
        if not re.search(pattern, text):
            add_finding(
                findings,
                title="Определение курса",
                category="context_extraction",
                severity=severity,
                expected="Курс работы определяется из содержимого документа",
                found="Не удалось определить курс автоматически",
                location="титульный лист/документ",
                recommendation="Добавьте явное указание курса на титульном листе",
            )

    if params.get("detect_authors_count", True):
        labels = [str(x).lower() for x in params.get("authors_labels", [])]
        lower = text.lower()
        if labels and not any(label in lower for label in labels):
            add_finding(
                findings,
                title="Определение количества авторов",
                category="context_extraction",
                severity=severity,
                expected="В документе есть блок с авторами",
                found="Не найден блок авторов/студентов",
                location="титульный лист/документ",
                recommendation="Добавьте блок с авторами на титульный лист",
            )


def run_work_formats_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("work_formats"):
        return

    severity = cfg.severity("work_formats", "error")
    params = cfg.params("work_formats")
    allowed_formats = [str(x).lower() for x in params.get("allowed_formats", [])]
    if not allowed_formats:
        return

    text = snapshot.full_text.lower()
    format_markers = {
        "academic": ["основная часть", "введение", "заключение"],
        "project_creative": ["теоретическая записка", "проектная записка", "творческая часть"],
    }

    detected: list[str] = []
    for fmt in allowed_formats:
        markers = format_markers.get(fmt, [])
        if markers and sum(1 for m in markers if m in text) >= 2:
            detected.append(fmt)

    if not detected:
        add_finding(
            findings,
            title="Определение формата работы",
            category="work_formats",
            severity=severity,
            expected=f"Один из форматов: {', '.join(allowed_formats)}",
            found="Не удалось определить формат по структуре",
            location="структура",
            recommendation="Проверьте названия ключевых разделов или задайте формат вручную",
        )


def run_layout_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("layout") or not snapshot.sections:
        return

    severity = cfg.severity("layout", "warning")
    params = cfg.params("layout")
    target = params.get("margins_mm", {"left": 30, "right": 15, "top": 20, "bottom": 25})
    tolerance = float(params.get("tolerance_mm", 1))
    labels = {"left": "левое", "right": "правое", "top": "верхнее", "bottom": "нижнее"}

    for sec_idx, section in enumerate(snapshot.sections):
        values = {
            "left": section.left_mm,
            "right": section.right_mm,
            "top": section.top_mm,
            "bottom": section.bottom_mm,
        }
        location = f"раздел {sec_idx + 1}" if len(snapshot.sections) > 1 else "документ"

        for key, expected in target.items():
            found = values.get(key)
            if found is None:
                continue
            if abs(float(found) - float(expected)) > tolerance:
                add_finding(
                    findings,
                    title=f"Поле страницы: {labels.get(key, key)}",
                    category="layout",
                    severity=severity,
                    expected=f"{expected} мм (±{tolerance} мм)",
                    found=f"{found} мм",
                    location=location,
                    recommendation="Исправьте параметры страницы в настройках документа",
                )


_SKIP_TYPO_STYLE_IDS = frozenset({
    "TOCHeading", "TOC1", "TOC2", "TOC3", "TOC4", "TOC5",
    "TOC6", "TOC7", "TOC8", "TOC9",
    "TableofFigures", "TableofAuthorities",
    "Caption", "Title", "Subtitle",
    "EndnoteText", "FootnoteText",
    "Header", "Footer", "CommentText", "BalloonText",
})

_SKIP_TYPO_STYLE_NAMES = frozenset({
    "toc heading", "table of figures", "table of authorities",
    "caption", "title", "subtitle",
    "endnote text", "footnote text",
    "header", "footer", "annotation text", "balloon text",
})

_SKIP_TYPO_NAME_PREFIXES = ("toc ", "toc\xa0", "index ")


def _is_skip_style_for_typography(paragraph) -> bool:
    if paragraph.style_id in _SKIP_TYPO_STYLE_IDS:
        return True
    lower = paragraph.style_name.lower()
    if lower in _SKIP_TYPO_STYLE_NAMES:
        return True
    return any(lower.startswith(p) for p in _SKIP_TYPO_NAME_PREFIXES)


_MAX_FINDINGS_PER_TYPE = 10


def run_typography_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("typography"):
        return

    severity = cfg.severity("typography", "warning")
    params = cfg.params("typography")
    body = params.get("body", {})

    expected_font = str(body.get("font", "Times New Roman")).lower()
    expected_size = float(body.get("size_pt", 14))
    expected_line_spacing = float(body.get("line_spacing", 1.5))
    expected_indent = float(body.get("first_line_indent_mm", 12.5))
    max_samples = int(params.get("max_paragraphs_sample", 120))

    counts: dict[str, int] = {"font": 0, "size": 0, "spacing": 0, "indent": 0}

    checked = 0
    for paragraph in snapshot.paragraphs:
        if not paragraph.text or paragraph.is_heading:
            continue
        if _is_skip_style_for_typography(paragraph):
            continue
        checked += 1
        if checked > max_samples:
            break

        if paragraph.runs_fonts and counts["font"] < _MAX_FINDINGS_PER_TYPE:
            font = paragraph.runs_fonts[0].lower()
            if font != expected_font:
                counts["font"] += 1
                add_finding(
                    findings,
                    title="Шрифт основного текста",
                    category="typography",
                    severity=severity,
                    expected=body.get("font", "Times New Roman"),
                    found=paragraph.runs_fonts[0],
                    location=f"абзац #{paragraph.index + 1}",
                    recommendation="Приведите основной текст к единому шрифту",
                )

        if paragraph.runs_size_pt and counts["size"] < _MAX_FINDINGS_PER_TYPE:
            size = paragraph.runs_size_pt[0]
            if abs(size - expected_size) > 0.2:
                counts["size"] += 1
                add_finding(
                    findings,
                    title="Размер шрифта",
                    category="typography",
                    severity=severity,
                    expected=f"{expected_size} pt",
                    found=f"{size} pt",
                    location=f"абзац #{paragraph.index + 1}",
                    recommendation="Установите единый размер шрифта для основного текста",
                )

        if paragraph.line_spacing and counts["spacing"] < _MAX_FINDINGS_PER_TYPE:
            if abs(paragraph.line_spacing - expected_line_spacing) > 0.2:
                counts["spacing"] += 1
                add_finding(
                    findings,
                    title="Межстрочный интервал",
                    category="typography",
                    severity=severity,
                    expected=str(expected_line_spacing),
                    found=str(paragraph.line_spacing),
                    location=f"абзац #{paragraph.index + 1}",
                    recommendation="Установите корректный межстрочный интервал",
                )

        if paragraph.first_line_indent_mm is not None and counts["indent"] < _MAX_FINDINGS_PER_TYPE:
            if abs(paragraph.first_line_indent_mm - expected_indent) > 1.0:
                counts["indent"] += 1
                add_finding(
                    findings,
                    title="Абзацный отступ",
                    category="typography",
                    severity=severity,
                    expected=f"{expected_indent} мм",
                    found=f"{paragraph.first_line_indent_mm} мм",
                    location=f"абзац #{paragraph.index + 1}",
                    recommendation="Установите корректный отступ первой строки",
                )

    for label, key in [("шрифт", "font"), ("размер шрифта", "size"), ("интервал", "spacing"), ("отступ", "indent")]:
        if counts[key] >= _MAX_FINDINGS_PER_TYPE:
            add_finding(
                findings,
                title=f"Типографика: {label} — ещё замечания",
                category="typography",
                severity="advice",
                expected="",
                found=f"Показаны первые {_MAX_FINDINGS_PER_TYPE} замечаний, проблема массовая",
                location="весь документ",
                recommendation="Выделите весь текст и установите единое форматирование",
            )


def run_structure_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("structure"):
        return

    severity = cfg.severity("structure", "error")
    params = cfg.params("structure")

    required = params.get("required_sections_in_order") or [
        {"titles_any_of": ["введение"]},
        {"titles_any_of": ["основная часть"]},
        {"titles_any_of": ["заключение"]},
        {"titles_any_of": ["список литературы", "список использованных источников"]},
    ]

    heading_entries = [
        (p.index, p.text.strip().lower())
        for p in snapshot.paragraphs
        if p.text and p.is_heading
    ]
    short_para_entries = [
        (p.index, p.text.strip().lower())
        for p in snapshot.paragraphs
        if p.text and len(p.text.strip()) < 100 and not p.is_heading
    ]

    cursor = -1

    for section in required:
        titles = [str(x).lower() for x in section.get("titles_any_of", [])]
        if not titles:
            continue

        found_para_idx = None
        found_title = None
        for para_idx, h_text in heading_entries:
            if any(t in h_text for t in titles):
                found_para_idx = para_idx
                found_title = h_text
                break

        if found_para_idx is None:
            for para_idx, p_text in short_para_entries:
                if any(t in p_text for t in titles):
                    found_para_idx = para_idx
                    found_title = p_text
                    break

        section_name = section.get("id") or titles[0]
        optional = bool(section.get("required") is False)
        if found_para_idx is None:
            if optional:
                continue
            add_finding(
                findings,
                title=f"Раздел «{section_name}»",
                category="structure",
                severity=severity,
                expected=f"Наличие раздела: {', '.join(titles)}",
                found="Не найден",
                location="структура",
                recommendation="Добавьте обязательный раздел в документ",
            )
            continue

        if found_para_idx < cursor:
            add_finding(
                findings,
                title=f"Порядок разделов: «{section_name}»",
                category="structure",
                severity=severity,
                expected="Разделы идут в заданной последовательности",
                found=f"Раздел найден вне ожидаемого порядка: {found_title}",
                location="структура",
                recommendation="Переставьте разделы согласно методическим требованиям",
            )
        cursor = found_para_idx


def run_volume_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("volume"):
        return

    severity = cfg.severity("volume", "warning")
    params = cfg.params("volume")

    chars_per_sheet = int(params.get("author_sheet_chars_with_spaces", 40000))
    minimum_sheets = float(params.get("min_author_sheets_default", 0.5))

    text = snapshot.full_text
    char_count = len(text)
    sheets = round(char_count / chars_per_sheet, 3) if chars_per_sheet > 0 else 0

    if sheets < minimum_sheets:
        add_finding(
            findings,
            title="Объём работы",
            category="volume",
            severity=severity,
            expected=f"Не менее {minimum_sheets} авторского листа",
            found=f"{sheets} авторского листа",
            location="весь документ",
            recommendation="Увеличьте объём основной части согласно требованиям",
        )


