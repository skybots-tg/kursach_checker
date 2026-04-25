"""Paragraph classification helpers for autofix.

Detects heading, TOC, list, and skip-worthy paragraphs by examining style
ids, names, numbering properties and outline levels.
"""
from __future__ import annotations

import re

from docx.oxml.ns import qn

from app.rules_engine.heading_detection import normalize_toc_entry
from app.rules_engine.style_resolve import walk_style_pPr

_HEADING_STYLE_IDS = frozenset(
    {f"Heading{i}" for i in range(1, 10)}
)
_SKIP_STYLE_IDS = frozenset(
    {f"TOC{i}" for i in range(1, 10)}
    | {"TOCHeading", "TableofFigures", "TableofAuthorities", "Caption", "Title",
       "Subtitle", "NoSpacing", "BalloonText", "MacroText", "EndnoteText",
       "FootnoteText", "Header", "Footer", "CommentText"}
)
_SKIP_STYLE_NAMES = frozenset({
    "toc heading", "table of figures", "table of authorities", "caption",
    "title", "subtitle", "no spacing", "balloon text", "macro text",
    "endnote text", "footnote text", "header", "footer", "annotation text",
})
_SKIP_NAME_PREFIXES = ("toc ", "toc\xa0", "index ")
_LIST_STYLE_IDS = frozenset({
    "ListParagraph", "ListBullet", "ListBullet2", "ListBullet3",
    "ListNumber", "ListNumber2", "ListNumber3",
    "ListContinue", "ListContinue2", "ListContinue3",
})
_LIST_STYLE_NAMES = frozenset({
    "list paragraph", "list bullet", "list bullet 2", "list bullet 3",
    "list number", "list number 2", "list number 3",
    "list continue", "list continue 2", "list continue 3",
})


def is_heading_para(paragraph) -> bool:
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _HEADING_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    if "heading" in sname or "заголов" in sname:
        return True
    for pPr in walk_style_pPr(paragraph):
        ol = pPr.find(qn("w:outlineLvl"))
        if ol is not None:
            val = ol.get(qn("w:val"))
            try:
                if val is not None and int(val) < 9:
                    return True
            except (TypeError, ValueError):
                pass
    return False


def should_skip_para(paragraph) -> bool:
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _SKIP_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    if sname in _SKIP_STYLE_NAMES:
        return True
    return any(sname.startswith(p) for p in _SKIP_NAME_PREFIXES)


def is_list_para(paragraph) -> bool:
    for pPr in walk_style_pPr(paragraph):
        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            numId = numPr.find(qn("w:numId"))
            if numId is not None and numId.get(qn("w:val")) != "0":
                return True
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _LIST_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    return sname in _LIST_STYLE_NAMES


def collect_toc_heading_levels(doc, toc_indices: set[int]) -> dict[str, int]:
    """Gather normalized TOC-entry titles -> heading level for promotion.

    Used as a *fallback* heading detector: when a body paragraph does not
    match the normal chapter/numbering regexes but the document's table
    of contents explicitly lists it as a section title, we still promote
    it to a Word heading.

    Returns a dict mapping ``normalize_toc_entry(text)`` -> ``level``.
    """
    result: dict[str, int] = {}
    paragraphs = doc.paragraphs
    for idx in toc_indices:
        if idx < 0 or idx >= len(paragraphs):
            continue
        raw = (paragraphs[idx].text or "").strip()
        if not raw or len(raw) > 250:
            continue
        key = normalize_toc_entry(raw)
        if not key:
            continue
        if key in ("содержание", "оглавление"):
            continue
        level = _infer_toc_entry_level(key)
        result[key] = level
    return result


def _infer_toc_entry_level(normalized: str) -> int:
    m = re.match(r"^(\d+(?:\.\d+)*)", normalized)
    if m:
        parts = m.group(1).split(".")
        return max(1, min(len(parts), 3))
    return 1
