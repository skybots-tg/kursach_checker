"""Autofix: sort bibliography alphabetically and number entries."""
from __future__ import annotations

import logging
import re

from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

_BIBLIOGRAPHY_HEADINGS = frozenset({
    "список литературы",
    "список использованной литературы",
    "список используемой литературы",
    "список используемых источников",
    "список использованных источников",
    "список использованных источников и литературы",
    "список используемых источников и литературы",
    "список использованных источников информации",
    "библиографический список",
    "библиография",
    "литература",
    "references",
    "bibliography",
    "list of references",
})

# Extra phrases to recognise bibliography headings with minor variations
# (punctuation, extra words after the core phrase, etc.).
_BIBLIOGRAPHY_PATTERN = re.compile(
    r"^\s*(?:"
    r"список(?:\s+(?:использованн(?:ых|ой)|используем(?:ых|ой)))?\s+(?:источник(?:ов|и)|литератур[ыа])"
    r"|библиографическ(?:ий|ая)\s+список"
    r"|библиография"
    r"|references"
    r"|bibliography"
    r")\s*[:.]?\s*$",
    re.IGNORECASE | re.UNICODE,
)

_NUM_PREFIX_RE = re.compile(r"^\s*(?:\[\d{1,3}\][\.)\s]?|\d{1,3}[\.)])\s*")
_NUMBERED_ENTRY_RE = re.compile(r"^\s*(?:\[\d{1,3}\][\.)\s]?|\d{1,3}[\.)])\s+\S")
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


def _find_bibliography_range(doc) -> tuple[int, int, int] | None:
    """Return ``(heading_idx, start_idx, end_idx)`` for the bibliography section.

    ``heading_idx`` is the paragraph index of the «Список литературы» heading,
    ``start_idx`` is the first paragraph after it and ``end_idx`` is exclusive.
    """
    paragraphs = doc.paragraphs
    bib_heading_idx: int | None = None

    for idx, para in enumerate(paragraphs):
        text = (para.text or "").strip()
        low = text.lower()
        if low in _BIBLIOGRAPHY_HEADINGS or _BIBLIOGRAPHY_PATTERN.match(low):
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

    return (bib_heading_idx, start, end)


def _strip_number_prefix(text: str) -> str:
    """Strip leading numeric prefixes ("1.", "[1]", "1)") one or more times.

    Bibliography entries sometimes contain double-numbering like "11.\t13. Ivanov"
    when they were manually copy-pasted; we drop every leading number so the
    alphabetical sort sees the author surname as the first significant token.
    """
    result = text
    for _ in range(4):
        stripped = _NUM_PREFIX_RE.sub("", result)
        if stripped == result:
            break
        result = stripped
    return result.strip()


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

    heading_idx, start, end = rng
    paragraphs = doc.paragraphs

    # Group contiguous paragraphs into "entries". Each entry begins with a
    # numbered paragraph (e.g. "1. Иванов..."); subsequent non-numbered
    # paragraphs are treated as continuation of the previous entry and are
    # moved together with it during sorting.
    entries: list[dict] = []  # each: {"idxs": [...], "text": "..."}
    for idx in range(start, end):
        text = (paragraphs[idx].text or "").strip()
        if not text:
            continue
        if _NUMBERED_ENTRY_RE.match(text):
            entries.append({"idxs": [idx], "text": text})
        else:
            if len(text) < 5:
                continue
            if entries:
                entries[-1]["idxs"].append(idx)
                entries[-1]["text"] = entries[-1]["text"] + " " + text

    if len(entries) < 2:
        return False

    sorted_entries = sorted(entries, key=lambda e: _sort_key(e["text"]))

    already_sorted = all(
        _sort_key(entries[i]["text"]) <= _sort_key(entries[i + 1]["text"])
        for i in range(len(entries) - 1)
    )

    already_numbered = all(
        re.match(r"^\s*\d{1,3}[\.)]\s", e["text"]) for e in entries
    )

    if already_sorted and already_numbered:
        return False

    if not already_sorted:
        heading_elem = paragraphs[heading_idx]._element
        parent = heading_elem.getparent()
        if parent is None:
            return False

        all_entry_elements: list = []
        sorted_elements_groups: list[list] = []
        for e in entries:
            all_entry_elements.extend(paragraphs[i]._element for i in e["idxs"])
        for e in sorted_entries:
            sorted_elements_groups.append(
                [paragraphs[i]._element for i in e["idxs"]]
            )

        for elem in all_entry_elements:
            el_parent = elem.getparent()
            if el_parent is not None:
                el_parent.remove(elem)

        heading_pos = list(parent).index(heading_elem)
        insert_point = heading_pos + 1
        while insert_point < len(parent):
            child = parent[insert_point]
            if child.tag != qn("w:p"):
                break
            child_text = "".join(
                (t.text or "") for t in child.iter(qn("w:t"))
            ).strip()
            if child_text:
                break
            insert_point += 1

        cursor = insert_point
        for group in sorted_elements_groups:
            for elem in group:
                parent.insert(cursor, elem)
                cursor += 1

        details.append(
            f"Библиография: источники отсортированы по алфавиту ({len(entries)} шт.)"
        )

    refreshed = doc.paragraphs
    rng2 = _find_bibliography_range(doc)
    if rng2 is None:
        return True

    _, s2, e2 = rng2
    num = 1
    for idx in range(s2, e2):
        text = (refreshed[idx].text or "").strip()
        if not text:
            continue
        if not _NUMBERED_ENTRY_RE.match(text):
            continue
        clean = _strip_number_prefix(text)
        clean = _NUM_PREFIX_RE.sub("", clean).strip()
        new_text = f"{num}. {clean}"
        _set_paragraph_text(refreshed[idx], new_text)
        num += 1

    details.append(
        f"Библиография: источники пронумерованы 1–{num - 1}"
    )
    return True
