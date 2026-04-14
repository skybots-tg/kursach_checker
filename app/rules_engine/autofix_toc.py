"""Auto-generate a TOC field when the document has none."""
from __future__ import annotations

import logging
import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.rules_engine.heading_detection import TOC_LINE_TAIL_RE

logger = logging.getLogger(__name__)

_TOC_HEADING_RE = re.compile(r"^(содержание|оглавление)$", re.IGNORECASE)
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


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


def _build_toc_paragraph() -> OxmlElement:
    """Build a <w:p> containing a TOC field code."""
    p = OxmlElement("w:p")

    r1 = OxmlElement("w:r")
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    r1.append(fld_begin)
    p.append(r1)

    r2 = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-3" \h \z \u '
    r2.append(instr)
    p.append(r2)

    r3 = OxmlElement("w:r")
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r3.append(fld_sep)
    p.append(r3)

    r4 = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "Обновите оглавление (нажмите Ctrl+A, затем F9)"
    r4.append(t)
    p.append(r4)

    r5 = OxmlElement("w:r")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r5.append(fld_end)
    p.append(r5)

    return p


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


def insert_toc_field(doc, toc_indices: set[int], details: list[str]) -> bool:
    if _has_auto_toc(doc):
        return False

    body = doc.element.body
    paragraphs = doc.paragraphs
    toc_p = _build_toc_paragraph()

    for idx, para in enumerate(paragraphs):
        text = (para.text or "").strip()
        if _TOC_HEADING_RE.match(text):
            _remove_manual_toc_entries(doc, idx, details)
            para._element.addnext(toc_p)
            details.append("Оглавление: вставлено автоматическое поле TOC")
            return True

    for para in paragraphs:
        style_name = (getattr(para.style, "name", "") or "").lower()
        if "heading" in style_name or "заголов" in style_name:
            heading_p = _build_heading_paragraph("СОДЕРЖАНИЕ")
            para._element.addprevious(heading_p)
            heading_p.addnext(toc_p)
            details.append("Оглавление: создан заголовок «СОДЕРЖАНИЕ» и вставлено поле TOC")
            return True

    if len(body) > 0:
        body.insert(0, toc_p)
        details.append("Оглавление: вставлено автоматическое поле TOC")
        return True

    return False
