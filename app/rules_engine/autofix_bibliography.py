"""Autofix: sort bibliography alphabetically and number entries."""
from __future__ import annotations

import logging
import re

from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

_BIBLIOGRAPHY_HEADINGS = frozenset({
    "список литературы",
    "список использованных источников и литературы",
    "список использованных источников",
    "библиографический список",
    "list of references",
})

_NUM_PREFIX_RE = re.compile(r"^\s*(?:\[\d{1,3}\][\.)\s]?|\d{1,3}[\.)])\s*")
_LEADING_NONWORD_RE = re.compile(r"^[\s\W_]+", re.UNICODE)
_HEADING_STYLE_IDS = frozenset({f"Heading{i}" for i in range(1, 10)})

_RU_ALPHABET = (
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)
_RU_ORDER = {ch: i for i, ch in enumerate(_RU_ALPHABET)}


def _is_heading_para(paragraph) -> bool:
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _HEADING_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    return "heading" in sname or "заголов" in sname


def _find_bibliography_range(doc) -> tuple[int, int] | None:
    """Return (start_idx, end_idx) of bibliography entry paragraphs (exclusive end)."""
    paragraphs = doc.paragraphs
    bib_heading_idx: int | None = None

    for idx, para in enumerate(paragraphs):
        text = (para.text or "").strip().lower()
        if text in _BIBLIOGRAPHY_HEADINGS:
            bib_heading_idx = idx
            break

    if bib_heading_idx is None:
        return None

    start = bib_heading_idx + 1
    end = len(paragraphs)
    for idx in range(start, len(paragraphs)):
        para = paragraphs[idx]
        text = (para.text or "").strip()
        if not text:
            continue
        if _is_heading_para(para):
            end = idx
            break
        if text == text.upper() and len(text) > 3 and not re.match(r"^\s*[\[\d]", text):
            end = idx
            break

    return (start, end)


def _strip_number_prefix(text: str) -> str:
    return _NUM_PREFIX_RE.sub("", text).strip()


def _sort_key(text: str) -> tuple:
    """Locale-friendly alphabetical key for Russian/Latin bibliography entries.

    Russian goes first (а–я, with «ё» sorted right after «е»), Latin second.
    Digits, brackets and other punctuation are stripped from the head so
    GOST-style entries like "[1] Иванов..." sort by the actual author name.
    """
    stripped = _strip_number_prefix(text)
    stripped = _LEADING_NONWORD_RE.sub("", stripped)
    lower = stripped.lower()
    key: list[tuple[int, int]] = []
    for ch in lower:
        if ch in _RU_ORDER:
            key.append((0, _RU_ORDER[ch]))
        elif "a" <= ch <= "z":
            key.append((1, ord(ch)))
        elif ch.isdigit():
            key.append((2, ord(ch)))
        elif ch.isspace():
            key.append((3, 0))
    return tuple(key)


def _set_paragraph_text(paragraph, new_text: str) -> None:
    """Replace paragraph text while preserving formatting of the first run."""
    runs = paragraph.runs
    if not runs:
        return

    runs[0].text = new_text
    for run in runs[1:]:
        run.text = ""


def fix_bibliography_order_and_numbering(
    doc, details: list[str],
) -> bool:
    """Sort bibliography entries alphabetically and number them 1. 2. 3."""
    rng = _find_bibliography_range(doc)
    if rng is None:
        return False

    start, end = rng
    paragraphs = doc.paragraphs
    body = doc.element.body

    entries: list[tuple[int, str]] = []
    for idx in range(start, end):
        text = (paragraphs[idx].text or "").strip()
        if not text or len(text) < 10:
            continue
        entries.append((idx, text))

    if len(entries) < 2:
        return False

    sorted_entries = sorted(entries, key=lambda e: _sort_key(e[1]))

    already_sorted = all(
        _sort_key(entries[i][1]) <= _sort_key(entries[i + 1][1])
        for i in range(len(entries) - 1)
    )

    already_numbered = all(
        re.match(r"^\s*\d{1,3}[\.)]\s", entries[i][1])
        for i in range(len(entries))
    )

    if already_sorted and already_numbered:
        return False

    if not already_sorted:
        entry_elements = [paragraphs[idx]._element for idx, _ in entries]
        anchor = entry_elements[0]
        parent = anchor.getparent()

        sorted_elements = [paragraphs[idx]._element for idx, _ in sorted_entries]
        for elem in sorted_elements:
            parent.remove(elem)

        insert_after = anchor
        parent.remove(anchor)
        insert_point = None
        for i, child in enumerate(parent):
            if child.tag == qn("w:p"):
                p_text = "".join(
                    (t.text or "") for t in child.iter(qn("w:t"))
                ).strip().lower()
                if p_text in _BIBLIOGRAPHY_HEADINGS:
                    insert_point = i + 1
                    break

        if insert_point is None:
            insert_point = len(parent)

        skip_empty = insert_point
        while skip_empty < len(parent):
            child = parent[skip_empty]
            if child.tag == qn("w:p"):
                child_text = "".join(
                    (t.text or "") for t in child.iter(qn("w:t"))
                ).strip()
                if child_text:
                    break
            skip_empty += 1

        for i, elem in enumerate(sorted_elements):
            parent.insert(skip_empty + i, elem)

        details.append(
            f"Библиография: источники отсортированы по алфавиту ({len(entries)} шт.)"
        )

    refreshed = doc.paragraphs
    rng2 = _find_bibliography_range(doc)
    if rng2 is None:
        return True

    s2, e2 = rng2
    num = 1
    for idx in range(s2, e2):
        text = (refreshed[idx].text or "").strip()
        if not text or len(text) < 10:
            continue
        clean = _strip_number_prefix(text)
        new_text = f"{num}. {clean}"
        _set_paragraph_text(refreshed[idx], new_text)
        num += 1

    details.append(
        f"Библиография: источники пронумерованы 1–{num - 1}"
    )
    return True
