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
  «Приложение N» paragraph **anywhere in the body after that parent**
  is demoted to plain body text (``outlineLvl`` removed, ``pStyle``
  reset off ``HeadingN``). Earlier versions only demoted children that
  appeared in a tight consecutive block right after the parent — but
  real coursework appendices have several pages of body text between
  the individual «Приложение N» titles, so the children kept their
  ``Heading 2`` style and reappeared in the auto-TOC after Word
  refreshed the field.
* If no plural divider exists, a synthetic one is inserted before the
  very first **body** «Приложение N» heading, inheriting its
  page-break-before so the appendix block still starts on a fresh
  page. «Приложение N» entries that live inside a manually typed
  Table of Contents (``Содержание`` / ``Оглавление``) at the start
  of the document are recognised and skipped — otherwise the parent
  would be inserted INTO the TOC, pushing the appendix block in
  front of «Введение».

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
_PARENT_TEXT = "ПРИЛОЖЕНИЯ"


def _para_text(p_elem) -> str:
    """Concatenate text of *p_elem* preserving ``<w:tab/>`` and ``<w:br/>``.

    Tab characters in particular matter for TOC detection: students
    typically separate the title from the page number with a single
    Tab («Введение\\t3»), and our heuristic ``_looks_like_toc_entry``
    looks for that tab to recognise the TOC tail. Without preserving
    the tab the joined text would read «Введение3» and the heuristic
    would miss every entry in the listing.
    """
    parts: list[str] = []
    t_tag = qn("w:t")
    tab_tag = qn("w:tab")
    br_tag = qn("w:br")
    for child in p_elem.iter():
        if child.tag == t_tag:
            parts.append(child.text or "")
        elif child.tag == tab_tag:
            parts.append("\t")
        elif child.tag == br_tag:
            parts.append("\n")
    return "".join(parts).strip()


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


_TOC_HEADING_WORDS = ("содержание", "оглавление", "table of contents", "contents")


def _is_toc_heading(text: str) -> bool:
    low = (text or "").strip().lower().rstrip(":.;")
    return low in _TOC_HEADING_WORDS


def _looks_like_toc_entry(text: str) -> bool:
    """Paragraph ends with a typical TOC tail («… 12» / dots+num / tab+num)."""
    if not text:
        return False
    if len(text) > 200:
        return False
    if re.search(r"(?:\.{2,}|\t|\u2026|\s{3,})\s*\d{1,4}\s*$", text):
        return True
    return False


_TOC_MARKER_RE = re.compile(
    r"^(?:"
    r"введение"
    r"|заключение"
    r"|выводы"
    r"|глава\s+\d"
    r"|раздел\s+\d"
    r"|chapter\s+\d"
    r"|\d+\s+глава"
    r"|\d{1,2}\.\d{1,2}"
    r"|[ivxlcm]{1,6}\s+[a-zа-яё]"
    r"|список\s+(?:использованн|используем|литератур|источник|терминов|сокращ)"
    r"|библиограф"
    r"|references"
    r"|bibliography"
    r")",
    re.IGNORECASE,
)


def _looks_like_toc_marker(text: str) -> bool:
    """Paragraph starts with a typical heading marker (Глава, 1.2., I, …).

    Used to absorb manual TOC entries that don't have a page-number
    tail but otherwise look like headings the student copied into a
    home-made TOC list.
    """
    return bool(_TOC_MARKER_RE.match((text or "").strip()))


_CHAPTER_NUMBER_HINTS = (
    "глав", "раздел", "часть", "приложен", "параграф",
    "chapter", "section", "part", "appendix",
)


def _normalize_for_dup(text: str) -> str:
    """Strip TOC tail / surrounding punctuation and lowercase so the
    same chapter title compares equal whether it appears as a TOC
    entry («Введение … 4») or a body heading («ВВЕДЕНИЕ»).

    Trailing page-number tails are stripped in two flavours:
      * decoration-separated («Введение……3», «Введение\\t3»,
        «Введение  3», «Введение3») — always stripped;
      * single-space-separated («Введение 3») — stripped only when
        the preceding word is **not** a chapter-number marker
        («глава 1», «выводы по главе 2», «приложение 3» keep their
        digit, otherwise neighbour entries would normalise to the
        same key and prematurely terminate the TOC scan).
    """
    base = re.sub(r"\s+", " ", text or "").strip().lower()
    base = re.sub(r"[\.\u2026]{2,}\s*\d+\s*$", "", base)
    base = re.sub(r"\s{2,}\d+\s*$", "", base)
    base = re.sub(r"\t+\d+\s*$", "", base)
    # «Введение3» — digit glued directly to a letter (no space).
    base = re.sub(r"([а-яёa-z])\d{1,4}\s*$", r"\1", base)
    # «Введение 3» — single-space-separated trailing page number.
    # Drop only when previous word is NOT a chapter marker.
    m = re.match(r"^(.*?)(\s+)(\d{1,4})\s*$", base)
    if m:
        head = m.group(1).rstrip()
        last_word = head.split(" ")[-1] if head else ""
        if not any(last_word.startswith(h) for h in _CHAPTER_NUMBER_HINTS):
            base = head
    base = base.rstrip(":.;\u2014\u2013- ")
    return base


def _find_toc_block_range(doc) -> tuple[int, int] | None:
    """Locate the manual TOC block in the document body.

    Returns ``(start_idx, end_idx_exclusive)`` over ``doc.element.body``
    children, or ``None`` if no manual TOC is present. ``start_idx``
    points at the «Содержание» / «Оглавление» heading paragraph, and
    ``end_idx_exclusive`` is the first body element that is **not**
    part of the TOC list.

    The scan is intentionally permissive: any paragraph after the TOC
    heading whose text either looks like a TOC entry, starts with a
    typical heading marker, or is blank is absorbed. The block ends
    as soon as we reach a paragraph whose normalised title was
    already seen earlier in the TOC — that's the body repeating
    «ВВЕДЕНИЕ» / «ЗАКЛЮЧЕНИЕ» / «Глава 1» from the listing — or
    a paragraph that is clearly outside the TOC (real heading style,
    long body prose, …). This catches manually typed TOCs that the
    body of the document later promotes to ``Heading 1`` (e.g.
    «Приложение А» listed in the TOC) — we want to know those
    positions BEFORE consolidation so we don't synthesise a parent
    on top of them.
    """
    children = _iter_body_children(doc)
    p_tag = qn("w:p")
    heading_idx: int | None = None
    for i, el in enumerate(children):
        if el.tag != p_tag:
            continue
        if _is_toc_heading(_para_text(el)):
            heading_idx = i
            break
    if heading_idx is None:
        return None

    blanks = 0
    last_match = heading_idx
    seen_norm: set[str] = set()
    for j in range(heading_idx + 1, len(children)):
        el = children[j]
        if el.tag != p_tag:
            break
        text = _para_text(el)
        if not text:
            blanks += 1
            if blanks > 4:
                break
            continue
        # Real Heading style → body has started, stop.
        pPr = el.find(qn("w:pPr"))
        if pPr is not None:
            ps = pPr.find(qn("w:pStyle"))
            sval = (ps.get(qn("w:val")) if ps is not None else "") or ""
            if sval.startswith("Heading") and j != heading_idx:
                break
        is_toc_like = (
            _looks_like_toc_entry(text)
            or _is_child(text)
            or _is_parent(text)
            or _looks_like_toc_marker(text)
        )
        if not is_toc_like:
            break
        norm = _normalize_for_dup(text)
        if norm and norm in seen_norm:
            # Same title we already absorbed earlier — body is
            # restating the section name. Stop without consuming.
            break
        if norm:
            seen_norm.add(norm)
        blanks = 0
        last_match = j
    return heading_idx, last_match + 1


def _is_inside_range(idx: int, rng: tuple[int, int] | None) -> bool:
    if rng is None:
        return False
    return rng[0] <= idx < rng[1]


def _find_first_parent(doc, *, skip_range=None) -> tuple[int, object] | None:
    """Locate the first plural «Приложения» divider paragraph in the body
    (outside *skip_range* if provided).

    Returns ``(child_index, paragraph_element)`` or ``None``.
    """
    for i, el in enumerate(_iter_body_children(doc)):
        if el.tag != qn("w:p"):
            continue
        if _is_inside_range(i, skip_range):
            continue
        text = _para_text(el)
        if _is_parent(text):
            return i, el
    return None


def _find_first_child(doc, *, skip_range=None) -> tuple[int, object] | None:
    """Locate the first numbered «Приложение N» paragraph in the body
    that is **outside** the manual TOC range (when given).

    Returns ``(child_index, paragraph_element)`` or ``None``.
    """
    for i, el in enumerate(_iter_body_children(doc)):
        if el.tag != qn("w:p"):
            continue
        if _is_inside_range(i, skip_range):
            continue
        text = _para_text(el)
        if _is_child(text):
            return i, el
    return None


def _collect_all_body_children(doc, parent_idx: int, *, skip_range=None) -> list[object]:
    """Gather every «Приложение N» paragraph whose body position is
    **after** *parent_idx* (and outside *skip_range*).

    Unlike the previous «consecutive block» heuristic, this walks the
    entire body. Real coursework appendices contain many pages of
    body text between the individual «Приложение 1 / 2 / 3 /…»
    headings, and we still want to demote all of them so they stop
    showing up as separate TOC entries when Word refreshes the field.
    """
    out: list[object] = []
    for j, el in enumerate(_iter_body_children(doc)):
        if j <= parent_idx:
            continue
        if el.tag != qn("w:p"):
            continue
        if _is_inside_range(j, skip_range):
            continue
        text = _para_text(el)
        if not text:
            continue
        if _is_child(text):
            out.append(el)
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

    # Manual TOC range — paragraphs whose «Приложение N» titles are
    # actually TOC entries, not body appendix headings. Synthesising a
    # parent on top of them would push the appendix block in front of
    # «Введение» (the customer's «приложения дублируются вперёд»).
    toc_range = _find_toc_block_range(doc)

    parent_hit = _find_first_parent(doc, skip_range=toc_range)
    first_child = _find_first_child(doc, skip_range=toc_range)

    if mode == "singular_numbered":
        if parent_hit is None:
            return False
        body = doc.element.body
        removed = 0
        for el in list(body.iter(qn("w:p"))):
            if _is_parent(_para_text(el)) and el.getparent() is body:
                # Don't remove TOC entries that happen to read
                # «Приложения». Only body-level dividers are eligible.
                idx = list(body).index(el)
                if _is_inside_range(idx, toc_range):
                    continue
                body.remove(el)
                removed += 1
        if removed:
            details.append(
                f"Приложения: убран дублирующий заголовок «Приложения» "
                f"({removed} шт.) — в TOC останутся «Приложение N»"
            )
            return True
        return False

    if first_child is None:
        # No body-level appendices → nothing to consolidate. (TOC
        # entries that mention appendices are intentionally ignored.)
        return False

    changed = False
    body = doc.element.body

    if parent_hit is None:
        # Synthesise a new parent paragraph just above the first body
        # «Приложение N». ``_take_page_break_before`` migrates the
        # existing ``pageBreakBefore`` from the child onto the parent
        # so the visual layout stays the same.
        first_idx, first_el = first_child
        _take_page_break_before(first_el)
        new_parent = _build_parent_paragraph()
        first_el.addprevious(new_parent)
        details.append(
            "Приложения: добавлен общий заголовок «ПРИЛОЖЕНИЯ» перед первым приложением"
        )
        changed = True
        try:
            parent_idx = list(body).index(new_parent)
        except ValueError:
            parent_idx = max(0, first_idx)
    else:
        parent_idx, parent_el = parent_hit
        if _normalize_parent_text(parent_el, details):
            changed = True

    # Demote EVERY body «Приложение N» heading after the parent — not
    # just consecutive ones. Customer documents have several pages of
    # body text between individual appendix titles; the previous
    # «consecutive block» heuristic missed those and they kept
    # showing up as separate TOC lines.
    following = _collect_all_body_children(doc, parent_idx, skip_range=toc_range)
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
