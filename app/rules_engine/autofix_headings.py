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
        if cfg.heading_level2plus_center:
            if paragraph.alignment != WD_PARAGRAPH_ALIGNMENT.CENTER:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                paragraph.paragraph_format.first_line_indent = Mm(0)
                details.append(
                    f"Заголовок #{idx + 1}: подзаголовок по центру"
                )
                return True
        elif paragraph.alignment == WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
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
        if cfg.heading_level2plus_center:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        else:
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


def enforce_subheading_alignment(doc, cfg, details: list[str]) -> bool:
    """Force every heading to a specific alignment.

    * level 1 (chapters / ВВЕДЕНИЕ / ЗАКЛЮЧЕНИЕ / СПИСОК ЛИТЕРАТУРЫ) →
      center when ``heading_level1_center`` is True.
    * level 2+ (subsections 1.1, 1.2…) → center when
      ``heading_level2plus_center`` is True.

    Runs independently of ``skip_headings`` safety flag because changing only
    alignment (and wiping red-line indent) is safe and matches the client's
    explicit request «название параграфа / главы по середине».
    """
    center1 = bool(getattr(cfg, "heading_level1_center", True))
    center2plus = bool(getattr(cfg, "heading_level2plus_center", True))
    if not center1 and not center2plus:
        return False

    chapters_changed = 0
    subs_changed = 0
    for para in doc.paragraphs:
        level = _para_heading_level(para)
        if level is None:
            continue
        if level == 1 and not center1:
            continue
        if level >= 2 and not center2plus:
            continue

        touched = False
        if para.alignment != WD_PARAGRAPH_ALIGNMENT.CENTER:
            para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            touched = True
        pf = para.paragraph_format
        if pf.first_line_indent is not None and int(pf.first_line_indent) != 0:
            pf.first_line_indent = Mm(0)
            touched = True
        if pf.left_indent is not None and int(pf.left_indent) != 0:
            pf.left_indent = Mm(0)
            touched = True
        if touched:
            if level == 1:
                chapters_changed += 1
            else:
                subs_changed += 1

    if chapters_changed:
        details.append(
            f"Главы: {chapters_changed} шт. выровнены по центру"
        )
    if subs_changed:
        details.append(
            f"Подзаголовки: {subs_changed} шт. выровнены по центру"
        )
    return (chapters_changed + subs_changed) > 0


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


_CHAPTER_PAGE_BREAK_RE = re.compile(
    r"^\s*(?:"
    r"глава\s+\d+"
    r"|введение"
    r"|заключение"
    r"|содержание"
    r"|оглавление"
    r"|список\s+(?:использованн|используем|литератур|источник)"
    r"|библиографическ(?:ий|ая)\s+список"
    r"|библиография"
    r"|приложение(?:\s+\S+)?"
    r"|аннотация"
    r"|реферат"
    r"|annotation"
    r"|abstract"
    r"|references"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)


def enforce_chapter_page_breaks(doc, details: list[str]) -> bool:
    """Force ``page_break_before`` on every top-level heading (Heading 1) and
    on any paragraph whose text matches a well-known chapter/section label.

    This runs independently of the generic per-paragraph section-break fix
    which is gated by a strict length limit (``len(text) <= 100``) and
    therefore missed long chapter titles like
    «Глава 1 Теоретические основы организации работы государственного…».
    """
    paragraphs = list(doc.paragraphs)
    changed = 0
    for idx, para in enumerate(paragraphs):
        if idx == 0:
            continue
        text = (para.text or "").strip()
        if not text:
            continue

        level = _para_heading_level(para)
        matches_chapter = bool(_CHAPTER_PAGE_BREAK_RE.match(text))
        if level != 1 and not matches_chapter:
            continue
        if len(text) > 200:
            continue

        if _para_has_page_break_before(para):
            continue

        para.paragraph_format.page_break_before = True
        changed += 1

    if changed:
        details.append(
            f"Разрывы страниц: {changed} заголовок(ов) вынесено на новую страницу"
        )
    return changed > 0


def enforce_heading_bold(doc, cfg, details: list[str]) -> bool:
    """Ensure every Heading 1/2/3 paragraph has all runs set to bold.

    Operates at the XML level so that inherited style cascading and mixed
    explicit run properties no longer leave part of a heading un-bold. Runs
    independently of the ``skip_headings`` safety flag because the client
    explicitly asked for bold chapter/subsection headings.
    """
    if not getattr(cfg, "heading_bold", True):
        return False

    from docx.oxml import OxmlElement

    changed = 0
    for para in doc.paragraphs:
        level = _para_heading_level(para)
        if level is None or level > 3:
            continue
        touched = False
        for r_elem in para._element.iter(qn("w:r")):
            rPr = r_elem.find(qn("w:rPr"))
            if rPr is None:
                rPr = OxmlElement("w:rPr")
                r_elem.insert(0, rPr)
            for tag in ("w:b", "w:bCs"):
                el = rPr.find(qn(tag))
                if el is None:
                    el = OxmlElement(tag)
                    rPr.append(el)
                val = el.get(qn("w:val"))
                if val in ("0", "false"):
                    el.set(qn("w:val"), "1")
                    touched = True
                elif val is None:
                    touched = True
        if touched:
            changed += 1

    if changed:
        details.append(
            f"Заголовки: {changed} заголовок(ов) переведено в полужирный"
        )
    return changed > 0


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
