"""Informal list detection and conversion for autofix.

Detects groups of 2+ consecutive paragraphs that start with informal list markers
(like *, ·, •, -, —, –) but aren't formatted as Word-level lists, then replaces
the marker character with a proper list marker (em-dash by default).
"""
from __future__ import annotations

import logging

from docx.oxml.ns import qn

from app.rules_engine.style_resolve import walk_style_pPr

logger = logging.getLogger(__name__)

_DEFAULT_INFORMAL_MARKERS = frozenset("\u00b7\u2022*-\u2014\u2013")


def _has_word_numbering(paragraph) -> bool:
    for pPr in walk_style_pPr(paragraph):
        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            numId = numPr.find(qn("w:numId"))
            if numId is not None and numId.get(qn("w:val")) != "0":
                return True
    return False


def _starts_with_marker(text: str, markers: frozenset[str]) -> bool:
    stripped = text.lstrip()
    if not stripped or len(stripped) < 2:
        return False
    ch = stripped[0]
    if ch not in markers:
        return False
    if ch in ("-", "\u2013", "\u2014") and stripped[1].isdigit():
        return False
    return True


def _find_groups(
    paragraphs, markers: frozenset[str], toc_indices: set[int],
) -> list[list[int]]:
    groups: list[list[int]] = []
    current: list[int] = []
    for idx, para in enumerate(paragraphs):
        text = (para.text or "").strip()
        if not text or idx in toc_indices:
            if current:
                groups.append(current)
                current = []
            continue
        if _has_word_numbering(para):
            if current:
                groups.append(current)
                current = []
            continue
        if _starts_with_marker(text, markers):
            current.append(idx)
        else:
            if current:
                groups.append(current)
                current = []
    if current:
        groups.append(current)
    return groups


def _replace_marker_in_para(
    paragraph, markers: frozenset[str], target: str,
    label: str, details: list[str],
) -> bool:
    if not paragraph.runs:
        return False
    full = paragraph.text.lstrip()
    if not full or full[0] not in markers:
        return False
    for run in paragraph.runs:
        rt = run.text
        if not rt.strip():
            continue
        stripped = rt.lstrip()
        if stripped and stripped[0] in markers:
            ws = rt[: len(rt) - len(stripped)]
            rest = stripped[1:].lstrip()
            new_text = ws + target + " " + rest
            if new_text == rt:
                return False
            run.text = new_text
            details.append(f"{label}: неоформленный список \u2192 {target}")
            return True
        break
    return False


def convert_informal_lists(
    doc,
    marker_chars: list[str] | None,
    target_marker: str,
    min_consecutive: int,
    toc_indices: set[int],
    details: list[str],
) -> bool:
    markers = frozenset(marker_chars) if marker_chars else _DEFAULT_INFORMAL_MARKERS
    paragraphs = doc.paragraphs
    groups = _find_groups(paragraphs, markers, toc_indices)
    changed = False
    for group in groups:
        if len(group) < min_consecutive:
            continue
        for idx in group:
            para = paragraphs[idx]
            label = f"\u0410\u0431\u0437\u0430\u0446 #{idx + 1}"
            if _replace_marker_in_para(para, markers, target_marker, label, details):
                changed = True
    return changed
