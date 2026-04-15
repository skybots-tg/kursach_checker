"""Auto-generate a TOC field when the document has none.

The field uses cached display populated from actual document headings so the
TOC is immediately visible.  When opened in Word, pressing Ctrl+A → F9
updates page numbers.
"""
from __future__ import annotations

import logging
import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.rules_engine.heading_detection import TOC_LINE_TAIL_RE

logger = logging.getLogger(__name__)

_TOC_HEADING_RE = re.compile(r"^(содержание|оглавление)$", re.IGNORECASE)
_MAX_TOC_LEVEL = 3


def _has_auto_toc(doc) -> bool:
    body = doc.element.body
    for fld in body.iter(qn("w:fldChar")):
        if fld.get(qn("w:fldCharType")) != "begin":
            continue
        r_elem = fld.getparent()
        if r_elem is None:
            continue
        p_elem = r_elem.getparent()
        if p_elem is None:
            continue
        for sib_r in p_elem.iter(qn("w:r")):
            instr = sib_r.find(qn("w:instrText"))
            if instr is not None and instr.text and "TOC" in instr.text.upper():
                return True
    for fld in body.iter(qn("w:fldSimple")):
        instr = fld.get(qn("w:instr")) or ""
        if "TOC" in instr.upper():
            return True
    return False


# ── heading extraction ────────────────────────────────────────────────

def _get_heading_level(para) -> int | None:
    """Return 1-based heading level or *None*."""
    sid = getattr(para.style, "style_id", "") or ""
    for i in range(1, 10):
        if sid == f"Heading{i}":
            return i
    sname = (getattr(para.style, "name", "") or "").lower()
    for i in range(1, 10):
        if f"heading {i}" in sname or f"заголовок {i}" in sname:
            return i
    pPr = para._element.find(qn("w:pPr"))
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


def _collect_headings(doc) -> list[tuple[str, int]]:
    """Return ``[(text, level), ...]`` for headings up to ``_MAX_TOC_LEVEL``."""
    headings: list[tuple[str, int]] = []
    for para in doc.paragraphs:
        level = _get_heading_level(para)
        if level is None or level > _MAX_TOC_LEVEL:
            continue
        text = (para.text or "").strip()
        if not text or _TOC_HEADING_RE.match(text):
            continue
        headings.append((text, level))
    return headings


# ── XML builders ──────────────────────────────────────────────────────

def _build_toc_entry(text: str, level: int) -> OxmlElement:
    """Build a cached TOC entry paragraph with TOCx style."""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), f"TOC{level}")
    pPr.append(pStyle)
    if level > 1:
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), str((level - 1) * 240))
        pPr.append(ind)
    p.append(pPr)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    p.append(r)
    return p


def _build_toc_elements(
    headings: list[tuple[str, int]],
) -> tuple[OxmlElement, list[OxmlElement], OxmlElement]:
    """Return (begin_p, entry_paragraphs, end_p) for a multi-paragraph TOC field."""

    begin_p = OxmlElement("w:p")
    r1 = OxmlElement("w:r")
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    r1.append(fld_begin)
    begin_p.append(r1)

    r2 = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-3" \h \z \u '
    r2.append(instr)
    begin_p.append(r2)

    r3 = OxmlElement("w:r")
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r3.append(fld_sep)
    begin_p.append(r3)

    entries = [_build_toc_entry(text, level) for text, level in headings]

    if not entries:
        fallback = OxmlElement("w:p")
        r_fb = OxmlElement("w:r")
        t_fb = OxmlElement("w:t")
        t_fb.text = "Обновите оглавление (Ctrl+A, затем F9)"
        r_fb.append(t_fb)
        fallback.append(r_fb)
        entries = [fallback]

    end_p = OxmlElement("w:p")
    r_end = OxmlElement("w:r")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r_end.append(fld_end)
    end_p.append(r_end)

    return begin_p, entries, end_p


def _build_heading_paragraph(text: str, style_id: str = "Heading1") -> OxmlElement:
    """Build a <w:p> with a heading style."""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), style_id)
    pPr.append(pStyle)
    p.append(pPr)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    r.append(t)
    p.append(r)
    return p


def _remove_manual_toc_entries(doc, heading_idx: int, details: list[str]) -> bool:
    """Remove manually typed TOC lines that follow the TOC heading."""
    body = doc.element.body
    paragraphs = doc.paragraphs
    to_remove: list = []

    for para in paragraphs[heading_idx + 1:]:
        text = (para.text or "").strip()
        if not text:
            to_remove.append(para._element)
            continue
        style_name = (getattr(para.style, "name", "") or "").lower()
        is_heading = "heading" in style_name or "заголов" in style_name
        if is_heading or len(text) > 200:
            break
        if TOC_LINE_TAIL_RE.search(text) or _looks_like_toc_line(text):
            to_remove.append(para._element)
        else:
            break

    for elem in to_remove:
        body.remove(elem)

    if to_remove:
        details.append(f"Оглавление: удалено {len(to_remove)} ручных записей содержания")
    return len(to_remove) > 0


def _looks_like_toc_line(text: str) -> bool:
    """Heuristic: short line ending with a page number or dots+number."""
    if len(text) > 150:
        return False
    if re.search(r"\.{2,}\s*\d+\s*$", text):
        return True
    if re.search(r"\t+\d+\s*$", text):
        return True
    return False


def _insert_toc_after(anchor, doc, details: list[str]) -> bool:
    """Insert a multi-paragraph TOC field right after *anchor* element."""
    headings = _collect_headings(doc)
    begin_p, entries, end_p = _build_toc_elements(headings)

    last = anchor
    for elem in [begin_p, *entries, end_p]:
        last.addnext(elem)
        last = elem

    n_entries = len(headings)
    if n_entries:
        details.append(
            f"Оглавление: вставлено поле TOC ({n_entries} записей из заголовков)"
        )
    else:
        details.append("Оглавление: вставлено поле TOC (обновите в Word: Ctrl+A → F9)")
    return True


def insert_toc_field(doc, toc_indices: set[int], details: list[str]) -> bool:
    if _has_auto_toc(doc):
        return False

    body = doc.element.body
    paragraphs = doc.paragraphs

    for idx, para in enumerate(paragraphs):
        text = (para.text or "").strip()
        if _TOC_HEADING_RE.match(text):
            _remove_manual_toc_entries(doc, idx, details)
            return _insert_toc_after(para._element, doc, details)

    for para in paragraphs:
        style_name = (getattr(para.style, "name", "") or "").lower()
        if "heading" in style_name or "заголов" in style_name:
            heading_p = _build_heading_paragraph("СОДЕРЖАНИЕ")
            para._element.addprevious(heading_p)
            details.append("Оглавление: создан заголовок «СОДЕРЖАНИЕ»")
            return _insert_toc_after(heading_p, doc, details)

    if len(body) > 0:
        heading_p = _build_heading_paragraph("СОДЕРЖАНИЕ")
        body.insert(0, heading_p)
        details.append("Оглавление: создан заголовок «СОДЕРЖАНИЕ»")
        return _insert_toc_after(heading_p, doc, details)

    return False
