"""Autofix: position and align figure/table captions according to GOST.

Rules applied:
    * «Рисунок N — …» caption belongs **below** the figure and is centered.
    * «Таблица N — …» caption belongs **above** the table, left-aligned,
      without a red-line indent.

If the caption already sits in the right place we only normalise the
alignment/indent. If the caption is on the wrong side of its target
(e.g. «Рисунок 2» typed above the chart) the paragraph element is moved
next to the image / table in the document body.
"""
from __future__ import annotations

import logging
import re

from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Mm

logger = logging.getLogger(__name__)

_FIGURE_CAPTION_RE = re.compile(
    r"^\s*(?:рисунок|рис\.?|figure|fig\.?)\s*\d+",
    re.IGNORECASE | re.UNICODE,
)
_TABLE_CAPTION_RE = re.compile(
    r"^\s*таблица\s*\d+",
    re.IGNORECASE | re.UNICODE,
)
_SOURCE_LINE_RE = re.compile(
    r"^\s*(?:источник|source|примечание|note|составлено)\s*[:\u2014\u2013-]",
    re.IGNORECASE | re.UNICODE,
)

_DRAWING_TAGS = (qn("w:drawing"), qn("w:pict"), qn("w:object"))


def _para_has_image(p_elem) -> bool:
    """Return True if paragraph element contains inline/anchored image objects."""
    if p_elem is None or p_elem.tag != qn("w:p"):
        return False
    for tag in _DRAWING_TAGS:
        if p_elem.find(f".//{tag}") is not None:
            return True
    return False


def _prev_sibling(elem):
    sib = elem.getprevious()
    while sib is not None and sib.tag is etree_comment_tag():
        sib = sib.getprevious()
    return sib


def _next_sibling(elem):
    sib = elem.getnext()
    while sib is not None and sib.tag is etree_comment_tag():
        sib = sib.getnext()
    return sib


def etree_comment_tag():
    from lxml import etree
    return etree.Comment


def _prev_nonempty_sibling(elem):
    """Skip over empty paragraphs until we find a meaningful element."""
    sib = elem.getprevious()
    while sib is not None:
        if sib.tag == qn("w:p"):
            text = "".join(
                (t.text or "") for t in sib.iter(qn("w:t"))
            ).strip()
            if text or _para_has_image(sib):
                return sib
            sib = sib.getprevious()
            continue
        if sib.tag == qn("w:tbl"):
            return sib
        sib = sib.getprevious()
    return None


def _next_nonempty_sibling(elem):
    sib = elem.getnext()
    while sib is not None:
        if sib.tag == qn("w:p"):
            text = "".join(
                (t.text or "") for t in sib.iter(qn("w:t"))
            ).strip()
            if text or _para_has_image(sib):
                return sib
            sib = sib.getnext()
            continue
        if sib.tag == qn("w:tbl"):
            return sib
        sib = sib.getnext()
    return None


def _format_figure_caption(para) -> bool:
    """Center the caption paragraph and wipe red-line / left indents."""
    changed = False
    if para.alignment != WD_PARAGRAPH_ALIGNMENT.CENTER:
        para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        changed = True
    pf = para.paragraph_format
    if pf.first_line_indent is not None and int(pf.first_line_indent) != 0:
        pf.first_line_indent = Mm(0)
        changed = True
    if pf.left_indent is not None and int(pf.left_indent) != 0:
        pf.left_indent = Mm(0)
        changed = True
    return changed


def _format_table_caption(para) -> bool:
    """Left-align the table caption and remove red-line indent."""
    changed = False
    if para.alignment not in (WD_PARAGRAPH_ALIGNMENT.LEFT, None):
        para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        changed = True
    pf = para.paragraph_format
    if pf.first_line_indent is not None and int(pf.first_line_indent) != 0:
        pf.first_line_indent = Mm(0)
        changed = True
    if pf.left_indent is not None and int(pf.left_indent) != 0:
        pf.left_indent = Mm(0)
        changed = True
    return changed


def fix_caption_positions(doc, details: list[str]) -> bool:
    """Move figure captions below images, table captions above tables; align them."""
    changed = False
    fig_moved = 0
    fig_formatted = 0
    tbl_moved = 0
    tbl_formatted = 0

    for para in list(doc.paragraphs):
        text = (para.text or "").strip()
        if not text:
            continue
        p_elem = para._element
        if p_elem.getparent() is None:
            continue

        if _FIGURE_CAPTION_RE.match(text):
            # Figure caption: should be right below an image paragraph.
            prev = _prev_nonempty_sibling(p_elem)
            if prev is not None and prev.tag == qn("w:p") and _para_has_image(prev):
                if _format_figure_caption(para):
                    changed = True
                    fig_formatted += 1
                continue

            nxt = _next_nonempty_sibling(p_elem)
            if nxt is not None and nxt.tag == qn("w:p") and _para_has_image(nxt):
                # Caption is above the image; move it below.
                parent = p_elem.getparent()
                if parent is not None:
                    parent.remove(p_elem)
                    nxt.addnext(p_elem)
                    changed = True
                    fig_moved += 1
                if _format_figure_caption(para):
                    changed = True
                continue

            # No adjacent image — just align the caption (the image may sit
            # further away, but GOST layout still wants a centered caption).
            if _format_figure_caption(para):
                changed = True
                fig_formatted += 1
            continue

        if _TABLE_CAPTION_RE.match(text):
            # Table caption: should be right above a table (w:tbl).
            nxt = _next_nonempty_sibling(p_elem)
            if nxt is not None and nxt.tag == qn("w:tbl"):
                if _format_table_caption(para):
                    changed = True
                    tbl_formatted += 1
                continue

            prev = _prev_nonempty_sibling(p_elem)
            if prev is not None and prev.tag == qn("w:tbl"):
                parent = p_elem.getparent()
                if parent is not None:
                    parent.remove(p_elem)
                    prev.addprevious(p_elem)
                    changed = True
                    tbl_moved += 1
                if _format_table_caption(para):
                    changed = True
                continue

            if _format_table_caption(para):
                changed = True
                tbl_formatted += 1
            continue

    if fig_moved:
        details.append(f"Подписи: {fig_moved} подпись(ей) «Рисунок» перемещено под изображение")
    if fig_formatted:
        details.append(f"Подписи: {fig_formatted} подпись(ей) «Рисунок» выровнено по центру")
    if tbl_moved:
        details.append(f"Подписи: {tbl_moved} подпись(ей) «Таблица» перемещено над таблицу")
    if tbl_formatted:
        details.append(f"Подписи: {tbl_formatted} подпись(ей) «Таблица» выровнено по левому краю")
    return changed


def _zero_paragraph_spacing(p_elem) -> bool:
    """Force ``space_before=0`` / ``space_after=0`` and ``line=auto`` (1.0)
    on *p_elem*'s ``<w:spacing>``. Returns True if anything changed.

    Used to compress the visual block around a figure / table so the
    caption sits flush with the image / data and does not bleed into
    the surrounding body text.
    """
    from docx.oxml import OxmlElement
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_elem.insert(0, pPr)
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    changed = False
    if spacing.get(qn("w:before")) not in (None, "0"):
        spacing.set(qn("w:before"), "0")
        changed = True
    if spacing.get(qn("w:after")) not in (None, "0"):
        spacing.set(qn("w:after"), "0")
        changed = True
    if spacing.get(qn("w:beforeAutospacing")) not in (None, "0"):
        spacing.set(qn("w:beforeAutospacing"), "0")
        changed = True
    if spacing.get(qn("w:afterAutospacing")) not in (None, "0"):
        spacing.set(qn("w:afterAutospacing"), "0")
        changed = True
    return changed


def _drop_trailing_period(para) -> bool:
    """Strip a single trailing «.» from the last text run.

    Mirrors :func:`fix_caption_trailing_dot` from autofix_helpers but
    applies to the «Источник:» style of caption that we detect here
    rather than the figure/table caption itself. Keeps the period when
    it's actually an ellipsis («…»/«...»).
    """
    text = para.text.rstrip()
    if not text.endswith(".") or text.endswith(".."):
        return False
    t_elements = list(para._element.iter(qn("w:t")))
    for t_el in reversed(t_elements):
        s = (t_el.text or "").rstrip()
        if s and s.endswith(".") and not s.endswith(".."):
            tail = (t_el.text or "")[len(s):]
            t_el.text = s[:-1] + tail
            return True
        if s:
            break
    return False


def fix_source_caption_lines(doc, details: list[str]) -> bool:
    """Justify «Источник: …» / «Примечание: …» / «Составлено …» captions
    that follow a table and strip any trailing «.».

    Customer requirement (МЭО reference document):
        * Lines such as «Источник: составлено автором …» that sit
          underneath a table must be aligned **по ширине** (justified)
          rather than centered like the table caption above the table.
        * The trailing period at the end of that line must be removed.
        * The block must be visually tight — no extra space below the
          table itself nor between the «Источник» line and the next
          body paragraph.
    """
    changed = False
    fixed_align = 0
    stripped_dot = 0

    for para in list(doc.paragraphs):
        text = (para.text or "").strip()
        if not text or not _SOURCE_LINE_RE.match(text):
            continue
        # Only treat it as a table source caption when the previous
        # non-empty sibling is a table (or the caption directly follows
        # one). Otherwise it might be a regular bibliography note that
        # we shouldn't touch.
        prev = _prev_nonempty_sibling(para._element)
        if prev is None or prev.tag != qn("w:tbl"):
            continue

        if para.alignment != WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
            para.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            fixed_align += 1
            changed = True
        pf = para.paragraph_format
        if pf.first_line_indent is not None and int(pf.first_line_indent) != 0:
            pf.first_line_indent = Mm(0)
            changed = True
        if pf.left_indent is not None and int(pf.left_indent) != 0:
            pf.left_indent = Mm(0)
            changed = True

        if _drop_trailing_period(para):
            stripped_dot += 1
            changed = True

        if _zero_paragraph_spacing(para._element):
            changed = True

    if fixed_align:
        details.append(
            f"Подписи: {fixed_align} строка(и) «Источник» выровнено по ширине"
        )
    if stripped_dot:
        details.append(
            f"Подписи: убрана конечная точка в {stripped_dot} строке(ах) «Источник»"
        )
    return changed


def tighten_caption_block_layout(doc, details: list[str]) -> bool:
    """Compress the vertical space around figures, captions and tables.

    For every paragraph that:
        * contains an inline ``<w:drawing>`` (figure body), or
        * matches ``_FIGURE_CAPTION_RE`` (figure caption «Рисунок N…»),
          or
        * matches ``_TABLE_CAPTION_RE`` (table caption «Таблица N…»),
    we hard-zero ``<w:spacing w:before w:after>`` and turn off Word's
    *autospacing* flags. The line spacing of the figure paragraph
    itself is also forced to single (``line="240"``, ``lineRule="auto"``)
    so the inline image doesn't get a 30 % padding from the inherited
    1.3 multiplier.

    The «Источник» caption gets the same treatment via
    :func:`fix_source_caption_lines`.
    """
    from docx.oxml import OxmlElement
    changed = False
    fig_paragraphs = 0
    capt_paragraphs = 0

    for para in list(doc.paragraphs):
        p_elem = para._element
        text = (para.text or "").strip()
        is_figure = _para_has_image(p_elem)
        is_caption = bool(text) and (
            _FIGURE_CAPTION_RE.match(text) or _TABLE_CAPTION_RE.match(text)
        )
        if not is_figure and not is_caption:
            continue
        touched = _zero_paragraph_spacing(p_elem)
        if is_figure:
            # Force single line spacing on the figure-bearing paragraph
            # so the inline drawing renders without the 1.3 multiplier
            # padding, which used to add a visible gap above the
            # caption.
            pPr = p_elem.find(qn("w:pPr"))
            if pPr is None:
                pPr = OxmlElement("w:pPr")
                p_elem.insert(0, pPr)
            spacing = pPr.find(qn("w:spacing"))
            if spacing is None:
                spacing = OxmlElement("w:spacing")
                pPr.append(spacing)
            if spacing.get(qn("w:line")) != "240":
                spacing.set(qn("w:line"), "240")
                spacing.set(qn("w:lineRule"), "auto")
                touched = True
        if touched:
            changed = True
            if is_figure:
                fig_paragraphs += 1
            if is_caption:
                capt_paragraphs += 1

    if fig_paragraphs:
        details.append(
            f"Рисунки: убраны лишние отступы вокруг изображений ({fig_paragraphs} шт.)"
        )
    if capt_paragraphs:
        details.append(
            f"Подписи рисунков/таблиц: интервал до/после обнулён ({capt_paragraphs} шт.)"
        )
    return changed
