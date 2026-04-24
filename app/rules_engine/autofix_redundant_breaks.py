"""Remove manual page-break paragraphs that became redundant once the
adjacent heading received ``pageBreakBefore``.

Students often type a chapter heading and then press Ctrl+Enter (manual
page break) right after it so that the body of the chapter starts on a
fresh page. After ``enforce_chapter_page_breaks`` promotes such headings
to ``Heading 1`` with ``pageBreakBefore``, the manual ``<w:br
w:type="page"/>`` becomes redundant and produces an empty page between
the heading and the body — exactly what users complain about for the
«Список использованных источников» heading.

This pass scans for empty paragraphs whose only content is a manual page
break and removes them when they sit immediately before or after a
heading paragraph that already carries ``pageBreakBefore``.
"""
from __future__ import annotations

from docx.oxml.ns import qn


_P_TAG = qn("w:p")
_R_TAG = qn("w:r")
_BR_TAG = qn("w:br")
_PPR_TAG = qn("w:pPr")
_RPR_TAG = qn("w:rPr")
_T_TAG = qn("w:t")
_BOOKMARK_START_TAG = qn("w:bookmarkStart")
_BOOKMARK_END_TAG = qn("w:bookmarkEnd")
_PAGE_BREAK_BEFORE_TAG = qn("w:pageBreakBefore")
_TYPE_ATTR = qn("w:type")


def _is_manual_page_break_only_paragraph(p_elem) -> bool:
    """True iff *p_elem* contains nothing visible besides one or more
    ``<w:br w:type="page"/>`` elements (and run/paragraph properties,
    bookmarks, empty ``<w:t/>``)."""
    has_page_break = False
    for child in p_elem:
        tag = child.tag
        if tag == _PPR_TAG:
            continue
        if tag in (_BOOKMARK_START_TAG, _BOOKMARK_END_TAG):
            continue
        if tag != _R_TAG:
            return False
        for rc in child:
            if rc.tag == _RPR_TAG:
                continue
            if rc.tag == _T_TAG:
                if (rc.text or "").strip():
                    return False
                continue
            if rc.tag == _BR_TAG and rc.get(_TYPE_ATTR) == "page":
                has_page_break = True
                continue
            return False
    return has_page_break


def _has_page_break_before(p_elem) -> bool:
    pPr = p_elem.find(_PPR_TAG)
    if pPr is None:
        return False
    el = pPr.find(_PAGE_BREAK_BEFORE_TAG)
    if el is None:
        return False
    val = el.get(qn("w:val"))
    return val not in ("0", "false")


def remove_redundant_manual_page_breaks(doc, details: list[str]) -> bool:
    """Drop empty manual-page-break paragraphs adjacent to a heading whose
    paragraph format already specifies ``pageBreakBefore``.

    Operates on every body-level ``<w:p>`` so it reaches paragraphs that
    ``doc.paragraphs`` would skip (e.g. inside content controls).
    """
    body = doc.element.body
    p_elements = list(body.iter(_P_TAG))

    removed = 0
    seen: set[int] = set()

    for idx, p_elem in enumerate(p_elements):
        if not _has_page_break_before(p_elem):
            continue
        # Look at the paragraph BEFORE the heading.
        prev = p_elements[idx - 1] if idx > 0 else None
        if prev is not None and id(prev) not in seen and _is_manual_page_break_only_paragraph(prev):
            seen.add(id(prev))
        # Look at the paragraph AFTER the heading.
        nxt = p_elements[idx + 1] if idx + 1 < len(p_elements) else None
        if nxt is not None and id(nxt) not in seen and _is_manual_page_break_only_paragraph(nxt):
            seen.add(id(nxt))

    for p_elem in p_elements:
        if id(p_elem) not in seen:
            continue
        parent = p_elem.getparent()
        if parent is None:
            continue
        parent.remove(p_elem)
        removed += 1

    if removed:
        details.append(
            f"Удалено {removed} лишних ручных разрывов страниц рядом с заголовками"
        )
        return True
    return False
