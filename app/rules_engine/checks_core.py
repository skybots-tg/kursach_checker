from __future__ import annotations

import re
from pathlib import Path

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

    first = snapshot.sections[0]
    values = {
        "left": first.left_mm,
        "right": first.right_mm,
        "top": first.top_mm,
        "bottom": first.bottom_mm,
    }
    labels = {"left": "левое", "right": "правое", "top": "верхнее", "bottom": "нижнее"}

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
                location="раздел 1",
                recommendation="Исправьте параметры страницы в настройках документа",
            )


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

    checked = 0
    for paragraph in snapshot.paragraphs:
        if not paragraph.text or paragraph.is_heading:
            continue
        checked += 1
        if checked > max_samples:
            break

        if paragraph.runs_fonts:
            font = paragraph.runs_fonts[0].lower()
            if font != expected_font:
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

        if paragraph.runs_size_pt:
            size = paragraph.runs_size_pt[0]
            if abs(size - expected_size) > 0.2:
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

        if paragraph.line_spacing and abs(paragraph.line_spacing - expected_line_spacing) > 0.2:
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

        if paragraph.first_line_indent_mm is not None and abs(paragraph.first_line_indent_mm - expected_indent) > 1.0:
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

    heading_titles = snapshot.heading_titles
    cursor = -1

    for section in required:
        titles = [str(x).lower() for x in section.get("titles_any_of", [])]
        if not titles:
            continue

        found_index = None
        found_title = None
        for idx, heading in enumerate(heading_titles):
            if any(t in heading for t in titles):
                found_index = idx
                found_title = heading
                break

        section_name = section.get("id") or titles[0]
        optional = bool(section.get("required") is False)
        if found_index is None:
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

        if found_index < cursor:
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
        cursor = found_index


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


def run_bibliography_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("bibliography"):
        return

    severity = cfg.severity("bibliography", "warning")
    params = cfg.params("bibliography")

    min_total = int(params.get("min_total_sources", 20))
    text = snapshot.full_text.lower()

    section_found = any(
        marker in text
        for marker in [
            "список литературы",
            "список использованных источников",
            "list of references",
        ]
    )
    if not section_found:
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

    refs = re.findall(r"(?m)^\s*(?:\[?\d{1,3}\]?)[\.)]\s+.+$", snapshot.full_text)
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


def run_objects_checks(snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding]) -> None:
    if not cfg.has("objects"):
        return

    severity = cfg.severity("objects", "warning")
    params = cfg.params("objects")
    if not params.get("forbid_linked_media", True):
        return

    if Path(snapshot.path).suffix.lower() != ".docx":
        return

    try:
        raw = Path(snapshot.path).read_bytes()
    except OSError:
        return

    if b'TargetMode="External"' in raw:
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
