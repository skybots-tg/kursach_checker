"""Heading semantics & numbering checks.

Detects pseudo-headings (numbered text without Word Heading style),
headings merged with body text, and validates heading numbering sequence.
"""
from __future__ import annotations

from app.rules_engine.docx_snapshot import DocumentSnapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.heading_detection import (
    detect_heading_candidate,
    detect_heading_merged_with_text,
    extract_heading_number_parts,
)
from app.rules_engine.rules_config import RulesConfig

_MAX_FINDINGS_PER_CHECK = 15


def run_heading_semantics_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    """Check that heading-like paragraphs use Word Heading styles and are standalone."""
    if not cfg.has("heading_semantics"):
        return

    severity = cfg.severity("heading_semantics", "warning")
    params = cfg.params("heading_semantics")

    detect_numbered = bool(params.get("detect_numbered_headings", True))
    require_styles = bool(params.get("require_word_heading_styles", True))
    require_standalone = bool(params.get("require_standalone_heading_paragraph", True))
    require_no_indent = bool(params.get("require_no_first_line_indent", True))
    require_non_justified = bool(params.get("require_non_justified_alignment", True))
    space_before = float(params.get("space_before_pt", 12))
    space_after = float(params.get("space_after_pt", 6))

    unstyled_count = 0
    merged_count = 0
    fmt_count = 0

    for para in snapshot.paragraphs:
        if not para.text or para.is_toc_entry:
            continue

        text = para.text.strip()
        candidate_level = detect_heading_candidate(text) if detect_numbered else None
        loc = f"абзац #{para.index + 1}"

        # Check 1: heading-like text without heading style
        if require_styles and candidate_level is not None and not para.is_heading:
            if unstyled_count < _MAX_FINDINGS_PER_CHECK:
                short = text[:60]
                add_finding(
                    findings,
                    title="Подзаголовок не размечен стилем",
                    category="heading_semantics",
                    severity=severity,
                    expected="Заголовок оформлен стилем Word «Заголовок»",
                    found=f"Обычный абзац: «{short}»",
                    location=loc,
                    recommendation=(
                        f"Примените стиль «Заголовок {candidate_level}», "
                        "чтобы он попал в автоматическое содержание"
                    ),
                )
            unstyled_count += 1

        # Check 2: heading merged with body text in one paragraph
        if require_standalone:
            merged = detect_heading_merged_with_text(text)
            if merged is not None:
                heading_part, _ = merged
                if merged_count < _MAX_FINDINGS_PER_CHECK:
                    add_finding(
                        findings,
                        title="Заголовок не отделён от основного текста",
                        category="heading_semantics",
                        severity=severity,
                        expected="Заголовок выделен в отдельный абзац",
                        found=f"Заголовок «{heading_part[:50]}» слит с текстом в одном абзаце",
                        location=loc,
                        recommendation="Перенесите основной текст в следующий абзац",
                    )
                merged_count += 1

        # Check 3: formatting of recognized headings (level 2/3)
        if para.is_heading and para.heading_level and para.heading_level >= 2:
            if require_no_indent and para.first_line_indent_mm and para.first_line_indent_mm > 1.0:
                if fmt_count < _MAX_FINDINGS_PER_CHECK:
                    add_finding(
                        findings,
                        title="Красная строка у заголовка",
                        category="heading_semantics",
                        severity=severity,
                        expected="Заголовок без абзацного отступа",
                        found=f"Отступ {para.first_line_indent_mm:.1f} мм",
                        location=loc,
                        recommendation="Уберите абзацный отступ (красную строку) у заголовка",
                    )
                fmt_count += 1

            if require_non_justified and para.alignment:
                if "JUSTIFY" in para.alignment.upper():
                    if fmt_count < _MAX_FINDINGS_PER_CHECK:
                        add_finding(
                            findings,
                            title="Выравнивание заголовка по ширине",
                            category="heading_semantics",
                            severity=severity,
                            expected="Заголовок выровнен по левому краю или по центру",
                            found="Выравнивание по ширине",
                            location=loc,
                            recommendation="Установите выравнивание по левому краю для подзаголовков",
                        )
                    fmt_count += 1

            if space_before > 0 and para.space_before_pt is not None:
                if para.space_before_pt < space_before * 0.5:
                    if fmt_count < _MAX_FINDINGS_PER_CHECK:
                        add_finding(
                            findings,
                            title="Интервал перед заголовком",
                            category="heading_semantics",
                            severity="advice",
                            expected=f"Не менее {space_before:.0f} пт",
                            found=f"{para.space_before_pt:.0f} пт",
                            location=loc,
                            recommendation="Увеличьте интервал перед заголовком",
                        )
                    fmt_count += 1

    if unstyled_count > _MAX_FINDINGS_PER_CHECK:
        add_finding(
            findings,
            title="Подзаголовки без стиля — ещё замечания",
            category="heading_semantics",
            severity="advice",
            expected="",
            found=f"Всего {unstyled_count} подзаголовков без стиля Word",
            location="весь документ",
            recommendation="Примените стили «Заголовок» ко всем разделам и подразделам",
        )

    if merged_count > _MAX_FINDINGS_PER_CHECK:
        add_finding(
            findings,
            title="Заголовки слиты с текстом — ещё замечания",
            category="heading_semantics",
            severity="advice",
            expected="",
            found=f"Всего {merged_count} случаев",
            location="весь документ",
            recommendation="Отделите все заголовки от основного текста",
        )


def run_heading_numbering_checks(
    snapshot: DocumentSnapshot, cfg: RulesConfig, findings: list[Finding],
) -> None:
    """Validate that heading numbers form a consistent hierarchy (1, 1.1, 1.2, 2, ...)."""
    if not cfg.has("heading_semantics"):
        return

    params = cfg.params("heading_semantics")
    if not bool(params.get("detect_numbered_headings", True)):
        return

    severity = cfg.severity("heading_semantics", "warning")

    numbered_headings: list[tuple[int, list[int], str]] = []
    for para in snapshot.paragraphs:
        if not para.text or para.is_toc_entry:
            continue
        text = para.text.strip()
        candidate = detect_heading_candidate(text)
        if candidate is None:
            continue
        parts = extract_heading_number_parts(text)
        if parts and len(parts) == candidate:
            numbered_headings.append((para.index, parts, text))

    if len(numbered_headings) < 2:
        return

    finding_count = 0
    prev_parts: list[int] | None = None
    for idx, parts, text in numbered_headings:
        if finding_count >= _MAX_FINDINGS_PER_CHECK:
            break
        if prev_parts is None:
            prev_parts = parts
            continue

        is_ok = _is_valid_sequence(prev_parts, parts)
        if not is_ok:
            prev_str = ".".join(str(p) for p in prev_parts)
            curr_str = ".".join(str(p) for p in parts)
            add_finding(
                findings,
                title="Нарушена последовательность нумерации заголовков",
                category="heading_semantics",
                severity=severity,
                expected=f"Последовательный номер после {prev_str}",
                found=f"Номер {curr_str}",
                location=f"абзац #{idx + 1}",
                recommendation="Проверьте и исправьте нумерацию заголовков",
            )
            finding_count += 1
        prev_parts = parts


def _is_valid_sequence(prev: list[int], curr: list[int]) -> bool:
    """Check if *curr* is a valid successor of *prev* in heading hierarchy."""
    if len(curr) == len(prev):
        expected = prev[:-1] + [prev[-1] + 1]
        return curr == expected
    if len(curr) == len(prev) + 1:
        return curr[:-1] == prev and curr[-1] == 1
    if len(curr) < len(prev):
        parent = prev[:len(curr) - 1]
        return curr[:-1] == parent and curr[-1] == prev[len(curr) - 1] + 1
    return False
