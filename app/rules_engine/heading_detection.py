"""Shared heading-candidate detection by text content.

Used by checks_headings, checks_advanced and autofix to recognize headings
that are typed as plain paragraphs without Word heading styles.
"""
from __future__ import annotations

import re

# ── Regex patterns (moved from checks_advanced to remove private-import coupling) ──

CHAPTER_RE = re.compile(
    r"^[^\w]*(?:(?:глава|chapter|раздел)\s+\d|\d+\s+глава)",
    re.IGNORECASE,
)
TOC_LINE_TAIL_RE = re.compile(r"\s{2,}\d[\d\-–—]+")

# ── Known structural section names ──────────────────────────────────

KNOWN_SECTION_TITLES: frozenset[str] = frozenset({
    "введение",
    "заключение",
    "выводы",
    "список литературы",
    "список использованных источников",
    "список использованных источников и литературы",
    "библиографический список",
    "содержание",
    "оглавление",
    "аннотация",
    "приложение",
    "приложения",
    "список сокращений",
    "список сокращений и условных обозначений",
    "перечень сокращений",
    "глоссарий",
    "термины",
    "термины и определения",
    "определения",
    "определения и сокращения",
    "список терминов",
    "обозначения и сокращения",
})

# ── Heading-candidate regexes ───────────────────────────────────────

_LEVEL1_RE = re.compile(
    r"^(?:"
    r"глава\s+\d+\.?"
    r"|\d+\s+глава"
    r"|введение"
    r"|заключение"
    r"|выводы"
    r"|аннотация"
    r"|приложени[еяй](?:\s+[а-яА-ЯёЁa-zA-Z\d])?"
    r"|список\s+(?:литературы|использованных\s+источников"
    r"|использованных\s+источников\s+и\s+литературы"
    r"|сокращений(?:\s+и\s+условных\s+обозначений)?)"
    r"|библиографический\s+список"
    r"|содержание"
    r"|оглавление"
    r"|глоссарий"
    r"|термины(?:\s+и\s+определения)?"
    r"|определения(?:\s+и\s+сокращения)?"
    r"|список\s+терминов"
    r"|обозначения\s+и\s+сокращения"
    r")\.?\s*$",
    re.IGNORECASE,
)

_LEVEL2_RE = re.compile(r"^\d+\.\d+\.?\s+\S")
_LEVEL3_RE = re.compile(r"^\d+\.\d+\.\d+\.?\s+\S")
_LEVEL4_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+\.?\s+\S")

_CHAPTER_NUM_RE = re.compile(
    r"^(?:(?:глава|раздел|chapter)\s+(\d+)|(\d+)\s+глава)",
    re.IGNORECASE,
)

# Roman-numeral chapter prefix like "I Организационно-технологический раздел"
# or "II РАСЧЕТНО-ТЕХНОЛОГИЧЕСКАЯ ЧАСТЬ" — no word «Глава», just a roman
# numeral followed by at least one space and a substantive title.
_ROMAN_CHAPTER_RE = re.compile(
    r"^(?P<num>[IVXLCM]{1,6})\s+[А-ЯЁA-Z][\wА-ЯЁа-яё\- ]{2,}$",
)
# Appendix like "Приложение А. ..." or "Приложение А ..." (без точки)
_APPENDIX_RE = re.compile(
    r"^приложени[еяй]\s+[\dА-ЯЁA-Z]",
    re.IGNORECASE,
)

_MAX_HEADING_TEXT_LEN = 200
_ROMAN_VALID = frozenset({
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX",
    "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
    "XX",
})


def _looks_like_roman_chapter(text: str) -> bool:
    m = _ROMAN_CHAPTER_RE.match(text)
    if not m:
        return False
    return m.group("num") in _ROMAN_VALID


def detect_heading_candidate(text: str) -> int | None:
    """Return expected heading level (1-4) if *text* looks like a heading, else None.

    Only analyses text content — does not consider Word style or outline level.
    """
    t = text.strip()
    if not t or len(t) > _MAX_HEADING_TEXT_LEN:
        return None
    if _LEVEL1_RE.match(t):
        return 1
    if _CHAPTER_NUM_RE.match(t):
        return 1
    if _APPENDIX_RE.match(t):
        return 1
    if _looks_like_roman_chapter(t):
        return 1
    if _LEVEL4_RE.match(t):
        return 4
    if _LEVEL3_RE.match(t):
        return 3
    if _LEVEL2_RE.match(t):
        return 2
    return None


_TOC_TAIL_STRIP_RE = re.compile(
    r"(?:\s*\.{2,}\s*\d[\d\-\u2013\u2014]*\s*|\s{2,}\d[\d\-\u2013\u2014]*\s*|\t+\d[\d\-\u2013\u2014]*\s*)$"
)


def normalize_toc_entry(text: str) -> str:
    """Strip page-number tail, trailing punctuation and outer whitespace.

    Used to compare a body paragraph against a TOC entry — the TOC usually
    types the same title but suffixes a page number or a dotted leader, so
    a literal string equality check would fail.
    """
    t = text.strip()
    if not t:
        return ""
    t = _TOC_TAIL_STRIP_RE.sub("", t)
    t = t.rstrip(" .:;\t")
    return re.sub(r"\s+", " ", t).strip().lower()


def detect_heading_via_toc(text: str, toc_titles: set[str] | dict[str, int]) -> int | None:
    """Return heading level when *text* matches a known TOC entry.

    ``toc_titles`` may be either a ``set`` of normalized titles (all treated
    as level 1) or a mapping ``{title -> level}`` when the caller already
    figured out the hierarchy from section numbering.
    """
    if not toc_titles:
        return None
    key = normalize_toc_entry(text)
    if not key:
        return None
    if isinstance(toc_titles, dict):
        return toc_titles.get(key)
    return 1 if key in toc_titles else None


_HEADING_PREFIX_RE = re.compile(
    r"^("
    r"\d+\.\d+\.\d+\.\d+\.?\s+"
    r"|\d+\.\d+\.\d+\.?\s+"
    r"|\d+\.\d+\.?\s+"
    r"|(?:глава|раздел|chapter)\s+\d+\.?\s*"
    r")",
    re.IGNORECASE,
)

_MIN_BODY_AFTER_HEADING = 80


def detect_heading_merged_with_text(text: str) -> tuple[str, str] | None:
    """Return (heading_part, body_part) if heading is glued to body text in one paragraph."""
    t = text.strip()
    m = _HEADING_PREFIX_RE.match(t)
    if not m:
        return None
    prefix = m.group(0)
    rest = t[m.end():]
    dot_pos = rest.find(".")
    if dot_pos == -1:
        return None
    heading_title = rest[:dot_pos].strip()
    body_after = rest[dot_pos + 1:].strip()
    if len(body_after) >= _MIN_BODY_AFTER_HEADING and len(heading_title) < 120:
        return (prefix + heading_title, body_after)
    return None


def extract_heading_number_parts(text: str) -> list[int] | None:
    """Extract hierarchical number from heading text, e.g. '2.3.1' -> [2, 3, 1]."""
    t = text.strip()
    m = re.match(r"^(\d+(?:\.\d+)*)", t)
    if not m:
        chapter_m = _CHAPTER_NUM_RE.match(t)
        if chapter_m:
            num = chapter_m.group(1) or chapter_m.group(2)
            return [int(num)]
        return None
    parts = m.group(1).split(".")
    try:
        return [int(p) for p in parts if p]
    except ValueError:
        return None
