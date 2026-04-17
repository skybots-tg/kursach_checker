"""Heading-related autofix helpers: formatting existing headings and promoting candidates."""
from __future__ import annotations

import logging
import re

from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
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
        if run.font.underline:
            run.font.underline = False
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


def _para_heading_level(paragraph) -> int | None:
    """Return Word heading level (1..9) or None if paragraph is not a heading."""
    sid = getattr(paragraph.style, "style_id", "") or ""
    for i in range(1, 10):
        if sid == f"Heading{i}":
            return i
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    for i in range(1, 10):
        if f"heading {i}" in sname or f"заголовок {i}" in sname:
            return i
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is not None:
        ol = pPr.find(qn("w:outlineLvl"))
        if ol is not None:
            try:
                val = int(ol.get(qn("w:val"), "9"))
                if val < 9:
                    return val + 1
            except (TypeError, ValueError):
                pass
    return None


def _para_has_page_break_before(paragraph) -> bool:
    if paragraph.paragraph_format.page_break_before:
        return True
    for br in paragraph._element.iter(qn("w:br")):
        if br.get(qn("w:type")) == "page":
            return True
    return False


def _build_empty_paragraph() -> "OxmlElement":
    """Build an empty <w:p/> with no runs — one blank line."""
    from docx.oxml import OxmlElement

    return OxmlElement("w:p")


def ensure_blank_before_subheadings(doc, details: list[str]) -> bool:
    """Ensure exactly one empty paragraph precedes every level-2+ heading
    within a chapter.

    Chapters (heading level 1) usually start on a new page via
    ``page_break_before`` and are skipped here. For sub-headings ``1.1``,
    ``1.2`` etc. we guarantee a single blank paragraph above, matching the
    client's request «один пробел между параграфами внутри главы».
    """
    paragraphs = list(doc.paragraphs)
    if len(paragraphs) < 2:
        return False

    changed = False
    inserted = 0

    for para in paragraphs:
        level = _para_heading_level(para)
        if level is None or level < 2:
            continue
        if _para_has_page_break_before(para):
            continue

        prev = para._element.getprevious()
        while prev is not None and prev.tag != qn("w:p"):
            prev = prev.getprevious()
        if prev is None:
            continue

        prev_text = "".join(
            (t.text or "") for t in prev.iter(qn("w:t"))
        ).strip()
        has_page_break = any(
            br.get(qn("w:type")) == "page" for br in prev.iter(qn("w:br"))
        )
        if has_page_break:
            continue

        if prev_text == "":
            continue

        blank = _build_empty_paragraph()
        para._element.addprevious(blank)
        inserted += 1
        changed = True

    if inserted:
        details.append(
            f"Отступы: добавлено {inserted} пустых абзаца(ев) перед подзаголовками"
        )
    return changed


def fix_remove_underline(paragraph, para_label: str, details: list[str]) -> bool:
    p_elem = paragraph._element
    changed = False
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is not None:
        rPr_default = pPr.find(qn("w:rPr"))
        if rPr_default is not None:
            el = rPr_default.find(qn("w:u"))
            if el is not None:
                rPr_default.remove(el)
                changed = True
    for r_elem in p_elem.iter(qn("w:r")):
        rPr = r_elem.find(qn("w:rPr"))
        if rPr is None:
            continue
        el = rPr.find(qn("w:u"))
        if el is not None:
            rPr.remove(el)
            changed = True
    if changed:
        details.append(f"{para_label}: подчёркивание убрано")
    return changed
