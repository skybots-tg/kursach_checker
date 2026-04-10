"""Heading-related autofix helpers: formatting existing headings and promoting candidates."""
from __future__ import annotations

import logging

from docx.shared import Mm, Pt

from app.rules_engine.autofix_helpers import is_field_code_run

logger = logging.getLogger(__name__)


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
    if changed:
        details.append(
            f"Заголовок #{idx + 1}: {cfg.heading_font}, {cfg.heading_size_pt} пт, полужирный"
        )
    return changed


def promote_to_heading(
    paragraph, level: int, idx: int, cfg, details: list[str],
) -> bool:
    """Assign Word Heading style to a paragraph detected as heading candidate by text."""
    target_style = f"Heading {level}"
    try:
        paragraph.style = paragraph.part.document.styles[target_style]
    except (KeyError, AttributeError):
        try:
            paragraph.style = target_style
        except Exception:
            logger.debug("Promote: style '%s' not found in document", target_style)
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
    details.append(f"Абзац #{idx + 1} → «Заголовок {level}»: {paragraph.text[:50]}")
    return True
