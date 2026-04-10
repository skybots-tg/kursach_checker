"""Shared heading-candidate detection by text content.

Used by checks_headings, checks_advanced and autofix to recognize headings
that are typed as plain paragraphs without Word heading styles.
"""
from __future__ import annotations

import re

# ── Regex patterns (moved from checks_advanced to remove private-import coupling) ──

CHAPTER_RE = re.compile(
    r"^[^\w]*(?:глава|chapter|раздел)\s+\d", re.IGNORECASE
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
    r"^(?:глава|раздел|chapter)\s+(\d+)", re.IGNORECASE
)

_MAX_HEADING_TEXT_LEN = 200


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
    if _LEVEL4_RE.match(t):
        return 4
    if _LEVEL3_RE.match(t):
        return 3
    if _LEVEL2_RE.match(t):
        return 2
    return None


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
            return [int(chapter_m.group(1))]
        return None
    parts = m.group(1).split(".")
    try:
        return [int(p) for p in parts if p]
    except ValueError:
        return None
