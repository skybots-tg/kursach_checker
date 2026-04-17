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
