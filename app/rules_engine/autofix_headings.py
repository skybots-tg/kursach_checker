"""Heading-related autofix helpers: formatting existing headings and promoting candidates."""
from __future__ import annotations

import logging
import re

from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Mm, Pt

from app.rules_engine.autofix_helpers import is_field_code_run

logger = logging.getLogger(__name__)

_HEADING_LEVEL_RE = re.compile(r"\d+")


def _detect_heading_level(paragraph) -> int | None:
    """Detect heading level from Word style name (e.g. 'Heading 2' -> 2)."""
    name = getattr(paragraph.style, "name", "") or ""
    m = _HEADING_LEVEL_RE.search(name)
    return int(m.group()) if m else None


def _resolve_heading_style(paragraph, level: int):
    """Get or create the Heading N style in the document."""
    doc = paragraph.part.document
    target_name = f"Heading {level}"
    try:
        return doc.styles[target_name]
    except KeyError:
        pass
    style = doc.styles.add_style(target_name, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles["Normal"]
    style.quick_style = True
    pf = style.paragraph_format
    pf.keep_with_next = True
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    return style


def _fix_alignment(paragraph, level: int | None, cfg, details: list[str], idx: int) -> bool:
    if level == 1 and cfg.heading_level1_center:
        if paragraph.alignment != WD_PARAGRAPH_ALIGNMENT.CENTER:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            details.append(f"Заголовок #{idx + 1}: выравнивание по центру")
            return True
    elif level is not None and level >= 2:
        if paragraph.alignment == WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            details.append(f"Заголовок #{idx + 1}: выравнивание по левому краю")
            return True
    return False


def fix_heading(paragraph, idx: int, cfg, details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run):
            continue
        if cfg.heading_font and run.font.name != cfg.heading_font:
            run.font.name = cfg.heading_font
            changed = True
        size_pt = float(run.font.size.pt) if run.font.size else None
        if size_pt is None or abs(size_pt - cfg.heading_size_pt) > 0.2:
            run.font.size = Pt(cfg.heading_size_pt)
            changed = True
        if cfg.heading_bold and not run.bold:
            run.bold = True
            changed = True

    level = _detect_heading_level(paragraph)
    if _fix_alignment(paragraph, level, cfg, details, idx):
        changed = True

    if changed:
        details.append(
            f"Заголовок #{idx + 1}: {cfg.heading_font}, {cfg.heading_size_pt} пт, полужирный"
        )
    return changed


def promote_to_heading(
    paragraph, level: int, idx: int, cfg, details: list[str],
) -> bool:
    """Assign Word Heading style to a paragraph detected as heading candidate by text."""
    try:
        style = _resolve_heading_style(paragraph, level)
        paragraph.style = style
    except Exception:
        logger.debug("Promote: cannot assign Heading %d", level, exc_info=True)
        return False

    for run in paragraph.runs:
        if is_field_code_run(run):
            continue
        if cfg.heading_font:
            run.font.name = cfg.heading_font
        run.font.size = Pt(cfg.heading_size_pt)
        if cfg.heading_bold:
            run.bold = True
    pf = paragraph.paragraph_format
    pf.first_line_indent = Mm(0)

    if level == 1 and cfg.heading_level1_center:
        paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    elif level >= 2:
        paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    details.append(f"Абзац #{idx + 1} → «Заголовок {level}»: {paragraph.text[:50]}")
    return True
