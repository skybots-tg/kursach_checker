"""Normalize formatting of an existing «Содержание» heading and its TOC
entries (auto-TOC fields wrapped in ``<w:sdt>`` content controls included).

Split out from ``autofix_toc.py`` to keep both modules under the project's
500-line cap.
"""
from __future__ import annotations

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.rules_engine.autofix_toc import (
    _TOC_HEADING_RE,
    _clear_bold_underline_in_paragraph,
    _normalize_existing_toc_heading,
)
from app.rules_engine.style_resolve import detect_toc_paragraph_indices


def _normalize_toc_entry_run_font(p_elem: OxmlElement, font_name: str, font_size_pt: float) -> bool:
    """Force every ``<w:r>`` in *p_elem* to use ``font_name`` / ``font_size_pt``
    (incl. complex script size) so TOC entries match body text instead of
    rendering in the theme/heading font.
    """
    changed = False
    size_half_pt = str(int(round(font_size_pt * 2)))
    for r_elem in p_elem.iter(qn("w:r")):
        rPr = r_elem.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            r_elem.insert(0, rPr)
            changed = True
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
            changed = True
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            if rFonts.get(qn(attr)) != font_name:
                rFonts.set(qn(attr), font_name)
                changed = True
        for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rFonts.get(qn(theme_attr)) is not None:
                del rFonts.attrib[qn(theme_attr)]
                changed = True
        for sz_tag in ("w:sz", "w:szCs"):
            sz = rPr.find(qn(sz_tag))
            if sz is None:
                sz = OxmlElement(sz_tag)
                rPr.append(sz)
                changed = True
            if sz.get(qn("w:val")) != size_half_pt:
                sz.set(qn("w:val"), size_half_pt)
                changed = True
    return changed


def _normalize_toc_entry_paragraph_format(p_elem: OxmlElement, line_spacing: float) -> bool:
    """Set 1.5 (or whatever cfg specifies) line spacing on a TOC entry, and
    drop any explicit space-before/space-after that would push entries apart.
    """
    changed = False
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_elem.insert(0, pPr)
        changed = True

    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
        changed = True

    line_240 = str(int(round(line_spacing * 240)))
    if spacing.get(qn("w:line")) != line_240:
        spacing.set(qn("w:line"), line_240)
        changed = True
    if spacing.get(qn("w:lineRule")) != "auto":
        spacing.set(qn("w:lineRule"), "auto")
        changed = True
    if spacing.get(qn("w:before")) not in (None, "0"):
        spacing.set(qn("w:before"), "0")
        changed = True
    if spacing.get(qn("w:after")) not in (None, "0"):
        spacing.set(qn("w:after"), "0")
        changed = True
    return changed


def _iter_sdt_toc_paragraphs(doc):
    """Yield ``(Paragraph, is_first_in_sdt)`` for every ``<w:p>`` nested in
    a ``<w:sdt>/<w:sdtContent>`` content control under the document body.

    Auto-generated tables of contents in Word are typically wrapped in such
    an SDT, and python-docx's ``doc.paragraphs`` silently skips paragraphs
    nested inside SDT — so without this helper neither the «Содержание»
    heading nor any of the TOC entries would be visible to the formatting
    pass.
    """
    from docx.text.paragraph import Paragraph

    body = doc.element.body
    p_tag = qn("w:p")
    sdt_content_tag = qn("w:sdtContent")

    for sdt in body.iter(qn("w:sdt")):
        content = sdt.find(sdt_content_tag)
        if content is None:
            continue
        is_first = True
        for sub in content.iterchildren():
            if sub.tag != p_tag:
                continue
            yield Paragraph(sub, doc), is_first
            is_first = False


def _normalize_toc_entry(p_elem: OxmlElement, font_name: str | None,
                         font_size_pt: float | None, line_spacing: float | None) -> bool:
    """Apply the full «plain body text» normalization to a single TOC entry
    paragraph: clear bold/underline, set body font/size, set line spacing.
    """
    changed = _clear_bold_underline_in_paragraph(p_elem)
    if font_name and font_size_pt:
        if _normalize_toc_entry_run_font(p_elem, font_name, font_size_pt):
            changed = True
    if line_spacing:
        if _normalize_toc_entry_paragraph_format(p_elem, line_spacing):
            changed = True
    return changed


def normalize_toc_heading_formatting(doc, details: list[str], *, cfg=None) -> bool:
    """Standalone pass: ensure the «Содержание»/«Оглавление» heading is
    centered/non-bold AND every TOC entry paragraph (auto field or manual)
    is rendered without bold/underline, with body font/size and line spacing.

    Runs even when ``generate_toc`` skips the document (because it already
    has a TOC field), so the client's requirement «убрать жирное выделение
    в содержании» is always applied to both the heading and the entries.

    Also descends into ``<w:sdt>`` content controls (auto-TOC fields stored
    by Word) — those paragraphs are invisible to ``doc.paragraphs`` and
    were the reason TOC entries kept appearing in the heading/theme font
    after autofix.
    """
    changed = False
    processed_elems: set = set()

    font_name = getattr(cfg, "font_name", None) if cfg is not None else None
    font_size_pt = getattr(cfg, "font_size_pt", None) if cfg is not None else None
    line_spacing = getattr(cfg, "line_spacing", None) if cfg is not None else None

    heading_elem = None
    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if _TOC_HEADING_RE.match(text):
            heading_elem = para._element
            if _normalize_existing_toc_heading(para, details):
                changed = True
            break

    sdt_entries_changed = 0
    for sdt_para, is_first in _iter_sdt_toc_paragraphs(doc):
        elem = sdt_para._element
        if elem in processed_elems:
            continue
        processed_elems.add(elem)
        text = (sdt_para.text or "").strip()
        if is_first and _TOC_HEADING_RE.match(text):
            if elem is not heading_elem:
                heading_elem = elem
                if _normalize_existing_toc_heading(sdt_para, details):
                    changed = True
            continue
        if _normalize_toc_entry(elem, font_name, font_size_pt, line_spacing):
            sdt_entries_changed += 1
            changed = True

    entry_paragraphs_changed = 0
    toc_indices = detect_toc_paragraph_indices(doc)
    if toc_indices:
        paragraphs = doc.paragraphs
        for idx in toc_indices:
            if idx >= len(paragraphs):
                continue
            p_elem = paragraphs[idx]._element
            if p_elem is heading_elem or p_elem in processed_elems:
                continue
            if _normalize_toc_entry(p_elem, font_name, font_size_pt, line_spacing):
                entry_paragraphs_changed += 1
                changed = True

    total_entries = entry_paragraphs_changed + sdt_entries_changed
    if total_entries:
        details.append(
            f"Оглавление: записи приведены к шрифту/интервалу основного текста ({total_entries} шт.)"
        )
    return changed
