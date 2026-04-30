"""Consolidate the «Приложения» / «Приложение N» block.

Coursework documents almost always contain several individual
«Приложение 1», «Приложение 2», … sections, sometimes preceded by an
explicit plural «Приложения» divider page and sometimes not. Both
shapes match ``_LEVEL1_RE`` in :mod:`heading_detection`, so the
heading-promotion pass turns every one of them into ``Heading 1`` —
the auto-generated TOC then ends up listing both the parent
«Приложения» and N child «Приложение 1…N» entries (≈ 9–11 lines for a
ВКР), which the customer considers visual clutter.

The customer-approved layout is:

    «Приложения»  (single TOC entry, plural form, no enumeration)

— individual «Приложение 1», «Приложение 2», … remain in the body but
do **not** appear as separate TOC entries. This module enforces that
layout regardless of whether the source document already contains a
plural divider:

* If a plural «Приложения» paragraph is found, every following
  «Приложение N» paragraph in the same block is demoted to plain body
  text (``outlineLvl`` removed, ``pStyle`` reset off ``HeadingN``).
* If no plural divider exists, a synthetic one is inserted before the
  very first «Приложение N» heading, inheriting its page-break-before
  so the appendix block still starts on a fresh page.

Behaviour is configurable through
:attr:`AutoFixConfig.appendix_consolidation`:

* ``"plural_only"`` (default) — the layout described above.
* ``"singular_numbered"`` — drop the plural divider, keep individual
  appendices as separate TOC entries.
* ``"off"`` — leave the document untouched.
"""
from __future__ import annotations

import logging
import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

# Plural form (any case ending) without a numeric/letter suffix:
# «Приложения», «Приложений», «Приложение» (single word, no number).
_PARENT_RE = re.compile(
    r"^приложени[еяй]\s*[:.\u2014\u2013-]?\s*$",
    re.IGNORECASE,
)
# Numbered/lettered child form: «Приложение 1», «Приложение А», …
_CHILD_RE = re.compile(
    r"^приложени[еяй]\s+[\dА-ЯЁA-Z][\)\.\s\u2014\u2013-]?",
    re.IGNORECASE,
)
# How many *empty* paragraphs we tolerate between the parent and the
# first child before we stop considering them a single block.
_MAX_BLANK_GAP = 5
_PARENT_TEXT = "ПРИЛОЖЕНИЯ"


def _para_text(p_elem) -> str:
    return "".join((t.text or "") for t in p_elem.iter(qn("w:t"))).strip()


def _is_parent(text: str) -> bool:
    return bool(_PARENT_RE.match(text))


def _is_child(text: str) -> bool:
    return bool(_CHILD_RE.match(text))


def _strip_heading_markers(p_elem) -> bool:
    """Detach paragraph from any ``HeadingN`` style and clear ``outlineLvl``.

    Used to demote an individual «Приложение N» entry so that the TOC
    field collector (``_collect_headings`` in autofix_toc) skips it.
    """
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        return False
    changed = False
    ps = pPr.find(qn("w:pStyle"))
    if ps is not None:
        val = (ps.get(qn("w:val")) or "").lower()
        if val.startswith("heading") or val in ("title", "subtitle"):
            pPr.remove(ps)
            changed = True
    ol = pPr.find(qn("w:outlineLvl"))
    if ol is not None:
        pPr.remove(ol)
        changed = True
    return changed


def _take_page_break_before(p_elem) -> bool:
    """Remove ``pageBreakBefore`` from *p_elem* and return True if it was set.

    When we synthesise a new parent paragraph above the first child, we
    move the page break onto the parent so the visual layout stays the
    same — the appendix block still starts on a fresh page, but the
    fresh page now begins with «ПРИЛОЖЕНИЯ» instead of «Приложение 1».
    """
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        return False
    pbb = pPr.find(qn("w:pageBreakBefore"))
    if pbb is None:
        return False
    pPr.remove(pbb)
    return True


def _ensure_page_break_before(p_elem) -> None:
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_elem.insert(0, pPr)
    if pPr.find(qn("w:pageBreakBefore")) is None:
        pPr.append(OxmlElement("w:pageBreakBefore"))


def _build_parent_paragraph(text: str = _PARENT_TEXT) -> OxmlElement:
    """Construct a centered, bold, ``Heading 1`` paragraph that visually
    matches the rest of the top-level structural headings (e.g.
    «ВВЕДЕНИЕ», «ЗАКЛЮЧЕНИЕ», «СПИСОК ЛИТЕРАТУРЫ»).

    The paragraph is fully self-contained so the rest of the autofix
    pipeline (``enforce_heading_font``, ``enforce_chapter_page_breaks``,
    TOC builder) can recognise it without any extra plumbing.
    """
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")

    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), "Heading1")
    pPr.append(pStyle)

    pbb = OxmlElement("w:pageBreakBefore")
    pPr.append(pbb)

    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    pPr.append(jc)

    ind = OxmlElement("w:ind")
    ind.set(qn("w:firstLine"), "0")
    ind.set(qn("w:left"), "0")
    pPr.append(ind)

    rPr_def = OxmlElement("w:rPr")
    b = OxmlElement("w:b")
    rPr_def.append(b)
    bCs = OxmlElement("w:bCs")
    rPr_def.append(bCs)
    rFonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), "Times New Roman")
    rPr_def.append(rFonts)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "28")
    rPr_def.append(sz)
    szCs = OxmlElement("w:szCs")
    szCs.set(qn("w:val"), "28")
    rPr_def.append(szCs)
    pPr.append(rPr_def)

    p.append(pPr)

    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    b2 = OxmlElement("w:b")
    rPr.append(b2)
    bCs2 = OxmlElement("w:bCs")
    rPr.append(bCs2)
    rFonts2 = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts2.set(qn(attr), "Times New Roman")
    rPr.append(rFonts2)
    sz2 = OxmlElement("w:sz")
    sz2.set(qn("w:val"), "28")
    rPr.append(sz2)
    szCs2 = OxmlElement("w:szCs")
    szCs2.set(qn("w:val"), "28")
    rPr.append(szCs2)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    p.append(r)
    return p


def _iter_body_children(doc):
    return list(doc.element.body)


def _find_first_parent(doc) -> tuple[int, object] | None:
    """Locate the first plural «Приложения» divider paragraph in the body.

    Returns ``(child_index, paragraph_element)`` or ``None``.
    """
    for i, el in enumerate(_iter_body_children(doc)):
        if el.tag != qn("w:p"):
            continue
        text = _para_text(el)
        if _is_parent(text):
            return i, el
    return None


def _find_first_child(doc) -> tuple[int, object] | None:
    """Locate the first numbered «Приложение N» paragraph in the body.

    Returns ``(child_index, paragraph_element)`` or ``None``.
    """
    for i, el in enumerate(_iter_body_children(doc)):
        if el.tag != qn("w:p"):
            continue
        text = _para_text(el)
        if _is_child(text):
            return i, el
    return None


def _collect_following_children(doc, start_idx: int) -> list[object]:
    """Walk forward from *start_idx* and gather every consecutive
    «Приложение N» paragraph (allowing up to :data:`_MAX_BLANK_GAP`
    intervening blanks). Stops at the first non-paragraph block (table,
    sectPr) or at a paragraph that is neither blank nor a child entry.
    """
    out: list[object] = []
    children = _iter_body_children(doc)
    blanks = 0
    for j in range(start_idx + 1, len(children)):
        el = children[j]
        if el.tag != qn("w:p"):
            break
        text = _para_text(el)
        if not text:
            blanks += 1
            if blanks > _MAX_BLANK_GAP:
                break
            continue
        if _is_child(text):
            out.append(el)
            blanks = 0
            continue
        # A real heading or any other content marks the end of the
        # appendix block.
        break
    return out


def _normalize_parent_text(p_elem, details: list[str]) -> bool:
    """Force the visible text of an existing parent paragraph to the
    canonical uppercase form ``"ПРИЛОЖЕНИЯ"`` so it matches the rest of
    the structural headings.
    """
    target = _PARENT_TEXT
    t_elements = list(p_elem.iter(qn("w:t")))
    if not t_elements:
        return False
    current = "".join((t.text or "") for t in t_elements).strip()
    if current == target:
        return False
    t_elements[0].text = target
    for tail in t_elements[1:]:
        tail.text = ""
    details.append("Приложения: заголовок приведён к виду «ПРИЛОЖЕНИЯ»")
    return True


def consolidate_appendix_block(
    doc, details: list[str], *, mode: str = "plural_only",
) -> bool:
    """Apply the requested appendix consolidation policy.

    Parameters
    ----------
    doc:
        The python-docx :class:`Document` being mutated in place.
    details:
        Run-log list collected by ``apply_safe_autofixes`` so the user
        sees what was changed in the report.
    mode:
        ``"plural_only"`` — keep / synthesise the plural «ПРИЛОЖЕНИЯ»
        divider and demote individual children so only one TOC entry
        remains. **Default** — matches the customer requirement.
        ``"singular_numbered"`` — drop the plural divider so each
        «Приложение N» becomes its own TOC entry.
        ``"off"`` — no-op.
    """
    if mode == "off":
        return False

    parent_hit = _find_first_parent(doc)
    first_child = _find_first_child(doc)

    if mode == "singular_numbered":
        # Drop redundant parent(s) so individual children remain.
        if parent_hit is None:
            return False
        body = doc.element.body
        # Re-scan every parent occurrence (rare, but possible).
        removed = 0
        for el in list(body.iter(qn("w:p"))):
            if _is_parent(_para_text(el)) and el.getparent() is body:
                body.remove(el)
                removed += 1
        if removed:
            details.append(
                f"Приложения: убран дублирующий заголовок «Приложения» "
                f"({removed} шт.) — в TOC останутся «Приложение N»"
            )
            return True
        return False

    # Default: plural_only.
    if first_child is None:
        # No appendices in the document → nothing to consolidate.
        return False

    changed = False
    body = doc.element.body
    children = _iter_body_children(doc)

    if parent_hit is None:
        # Synthesise a new parent paragraph just above the first child.
        first_idx, first_el = first_child
        had_break = _take_page_break_before(first_el)
        new_parent = _build_parent_paragraph()
        first_el.addprevious(new_parent)
        if not had_break:
            # Even when the original child paragraph had no explicit
            # page break, structural headings start on a new page in
            # the autofix-normalised layout. ``_build_parent_paragraph``
            # already inserts ``<w:pageBreakBefore/>``, so nothing else
            # to do here.
            pass
        details.append(
            "Приложения: добавлен общий заголовок «ПРИЛОЖЕНИЯ» перед первым приложением"
        )
        changed = True
        # Recompute children list now that we mutated the body.
        children = _iter_body_children(doc)
        # Walk forward from the new parent's index (idx of first child
        # is now first_idx + 1).
        try:
            new_parent_idx = list(body).index(new_parent)
        except ValueError:
            new_parent_idx = max(0, first_idx)
        following = _collect_following_children(doc, new_parent_idx)
    else:
        parent_idx, parent_el = parent_hit
        if _normalize_parent_text(parent_el, details):
            changed = True
        following = _collect_following_children(doc, parent_idx)

    demoted = 0
    for child_el in following:
        if _strip_heading_markers(child_el):
            demoted += 1
    if demoted:
        details.append(
            f"Приложения: индивидуальные «Приложение N» убраны из оглавления "
            f"({demoted} шт.) — остаётся одна строка «ПРИЛОЖЕНИЯ»"
        )
        changed = True

    return changed
