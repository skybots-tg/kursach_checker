"""Whitespace and indent normalization for autofix.

Handles leading whitespace stripping, left indent normalization for body text,
and collapsing of excessive consecutive empty paragraphs.
"""
from __future__ import annotations

import logging

from docx.oxml.ns import qn
from docx.shared import Mm

logger = logging.getLogger(__name__)

_WS_CHARS = " \t\xa0"


def fix_strip_leading_whitespace(
    paragraph, para_label: str, details: list[str],
) -> bool:
    """Strip leading spaces, tabs, and non-breaking spaces from paragraph runs."""
    if not paragraph.runs:
        return False

    changed = False
    for run in paragraph.runs:
        if not run.text:
            continue
        stripped = run.text.lstrip(_WS_CHARS)
        if stripped == run.text:
            break
        if stripped:
            run.text = stripped
            changed = True
            break
        run.text = ""
        changed = True

    if changed:
        details.append(f"{para_label}: ведущие пробелы убраны")
    return changed


def fix_normalize_left_indent(
    paragraph, para_label: str, details: list[str],
) -> bool:
    """Reset left indent to 0 for body text paragraphs."""
    pf = paragraph.paragraph_format
    changed = False

    if pf.left_indent is not None and int(pf.left_indent) > int(Mm(0.5)):
        pf.left_indent = Mm(0)
        changed = True

    pPr_el = paragraph._element.find(qn("w:pPr"))
    if pPr_el is not None:
        ind = pPr_el.find(qn("w:ind"))
        if ind is not None:
            for attr in (qn("w:left"), qn("w:start")):
                val = ind.get(attr)
                if val is None:
                    continue
                try:
                    if int(val) > 0:
                        ind.set(attr, "0")
                        changed = True
                except (ValueError, TypeError):
                    pass

    if changed:
        details.append(f"{para_label}: левый отступ обнулён")
    return changed


def _is_removable_empty(para) -> bool:
    if (para.text or "").strip():
        return False
    for child in para._element:
        tag = child.tag
        if tag == qn("w:pPr"):
            continue
        if tag in (qn("w:bookmarkStart"), qn("w:bookmarkEnd")):
            continue
        if tag == qn("w:r"):
            for rc in child:
                if rc.tag == qn("w:rPr"):
                    continue
                if rc.tag == qn("w:t") and not (rc.text or "").strip():
                    continue
                return False
        else:
            return False
    return True


def collapse_excessive_empty_paras(
    doc, max_consecutive: int, details: list[str],
) -> bool:
    """Remove consecutive empty paragraphs beyond *max_consecutive*."""
    paragraphs = list(doc.paragraphs)
    body = doc.element.body
    to_remove: list = []
    consecutive = 0

    for para in paragraphs:
        if _is_removable_empty(para):
            consecutive += 1
            if consecutive > max_consecutive:
                to_remove.append(para._element)
        else:
            consecutive = 0

    for elem in to_remove:
        try:
            body.remove(elem)
        except ValueError:
            pass

    if to_remove:
        details.append(f"Удалено {len(to_remove)} лишних пустых абзацев")
    return len(to_remove) > 0
