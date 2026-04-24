"""Split paragraphs that use soft line breaks (``<w:br/>``) instead of
proper paragraph marks.

A common student pattern in Word/Google Docs is to press Shift+Enter
between sentences. The result is one giant ``<w:p>`` element with a
chain of ``<w:br/>`` separators. To the eye it looks like several
paragraphs, but the document loses red-line indents (Word only applies
``firstLine`` to the first line of each paragraph) and breaks the rules
that expect each thought to live in its own ``<w:p>``.

This module rewrites such paragraphs in place: every ``<w:br/>`` becomes
the boundary between two new paragraphs, all of which inherit the
original ``<w:pPr>``. Runs and run properties are preserved exactly,
including hyperlinks. Empty resulting paragraphs are dropped.
"""
from __future__ import annotations

import copy
from typing import Iterator

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Don't touch tiny paragraphs — usually titles/captions or list items
# whose ``<w:br/>`` is intentional (e.g. address blocks on title pages).
_MIN_TEXT_LEN = 200
# Process only when the paragraph has multiple soft breaks. A single
# ``<w:br/>`` typically separates the title page header from the date,
# which is intentional formatting.
_MIN_BREAK_COUNT = 2

_BR_TAG = qn("w:br")
_R_TAG = qn("w:r")
_P_TAG = qn("w:p")
_PPR_TAG = qn("w:pPr")
_T_TAG = qn("w:t")
_HYPERLINK_TAG = qn("w:hyperlink")


def _iter_top_level_runs(p_elem) -> Iterator:
    """Yield top-level child elements that contain runs (``w:r`` or
    ``w:hyperlink``). Other children — bookmarks, comment markers,
    ``w:proofErr`` etc. — are returned as-is so we don't drop them."""
    for child in list(p_elem):
        if child.tag == _PPR_TAG:
            continue
        yield child


def _has_text(elem) -> bool:
    """Return True if *elem* (a run or hyperlink) yields any visible text."""
    for t in elem.iter(_T_TAG):
        if t.text and t.text.strip():
            return True
    return False


def _split_run_at_first_br(r_elem) -> list:
    """If *r_elem* contains one or more ``<w:br/>`` children, return a
    list of new run elements split at the FIRST break point — namely
    ``[before_br, after_br]``. ``after_br`` may itself contain more
    breaks; the caller should continue splitting it. ``rPr`` is cloned
    onto each new run so formatting is preserved.
    """
    rPr = r_elem.find(qn("w:rPr"))
    children = [c for c in r_elem if c.tag != qn("w:rPr")]
    br_idx = None
    for i, c in enumerate(children):
        if c.tag == _BR_TAG and (c.get(qn("w:type")) in (None, "textWrapping")):
            br_idx = i
            break
    if br_idx is None:
        return [r_elem]

    before = OxmlElement("w:r")
    after = OxmlElement("w:r")
    if rPr is not None:
        before.append(copy.deepcopy(rPr))
        after.append(copy.deepcopy(rPr))
    for c in children[:br_idx]:
        before.append(copy.deepcopy(c))
    for c in children[br_idx + 1:]:
        after.append(copy.deepcopy(c))
    return [before, after]


def _split_segment_at_breaks(elements: list) -> list[list]:
    """Walk *elements* (top-level paragraph children) and break them
    apart at every ``<w:br/>``. Returns a list of segments; each segment
    is the list of elements that should live in one resulting paragraph.
    """
    segments: list[list] = [[]]
    for elem in elements:
        if elem.tag == _R_TAG:
            queue = [elem]
            while queue:
                head = queue.pop(0)
                pieces = _split_run_at_first_br(head)
                if len(pieces) == 1:
                    segments[-1].append(pieces[0])
                else:
                    segments[-1].append(pieces[0])
                    segments.append([])
                    queue.insert(0, pieces[1])
        elif elem.tag == _HYPERLINK_TAG:
            segments[-1].append(copy.deepcopy(elem))
        else:
            segments[-1].append(copy.deepcopy(elem))
    return segments


def _segment_has_text(segment: list) -> bool:
    for elem in segment:
        if _has_text(elem):
            return True
    return False


def _build_paragraph(pPr_template, segment: list):
    """Construct a fresh ``<w:p>`` carrying a copy of *pPr_template* and
    the given *segment* of elements."""
    p = OxmlElement("w:p")
    if pPr_template is not None:
        p.append(copy.deepcopy(pPr_template))
    for elem in segment:
        p.append(elem)
    return p


def split_soft_break_paragraphs(doc, details: list[str]) -> bool:
    """Iterate every body paragraph and split it on ``<w:br/>`` when the
    paragraph is long enough to look like prose.

    Returns True if any change was applied.
    """
    body = doc.element.body
    changed_paragraphs = 0

    for p_elem in list(body.iter(_P_TAG)):
        # Skip headers / footers / TOC fields — their parents are not body.
        # ``iter`` walks every nested element so we filter by absence of
        # field code beginnings (TOC) and by minimum text length.
        text_chars = "".join(
            t.text or "" for t in p_elem.iter(_T_TAG)
        ).strip()
        if len(text_chars) < _MIN_TEXT_LEN:
            continue
        # Skip TOC field paragraphs (begin/instr/separate/end markers).
        if any(
            (fc.get(qn("w:fldCharType")) is not None)
            for fc in p_elem.iter(qn("w:fldChar"))
        ):
            continue
        if any("TOC" in (it.text or "").upper() for it in p_elem.iter(qn("w:instrText"))):
            continue

        breaks = [
            br for br in p_elem.iter(_BR_TAG)
            if br.get(qn("w:type")) in (None, "textWrapping")
        ]
        if len(breaks) < _MIN_BREAK_COUNT:
            continue

        pPr = p_elem.find(_PPR_TAG)
        elements = list(_iter_top_level_runs(p_elem))
        segments = _split_segment_at_breaks(elements)
        # Filter empty/whitespace-only segments.
        segments = [s for s in segments if _segment_has_text(s)]
        if len(segments) <= 1:
            continue

        parent = p_elem.getparent()
        if parent is None:
            continue
        anchor = p_elem
        new_paragraphs: list = []
        for seg in segments:
            new_p = _build_paragraph(pPr, seg)
            anchor.addnext(new_p)
            anchor = new_p
            new_paragraphs.append(new_p)
        parent.remove(p_elem)
        changed_paragraphs += 1

    if changed_paragraphs:
        details.append(
            f"Текст: разбито {changed_paragraphs} абзац(ев) с мягкими "
            f"переносами на отдельные абзацы"
        )
        return True
    return False
