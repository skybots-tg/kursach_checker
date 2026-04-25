"""Whitespace and indent normalization for autofix.

Handles leading whitespace stripping, left indent normalization for body text,
collapsing of excessive consecutive empty paragraphs, title page spacing,
and source-line single-spacing.
"""
from __future__ import annotations

import logging
import re

from docx.oxml.ns import qn
from docx.shared import Mm, Pt

logger = logging.getLogger(__name__)

_WS_CHARS = " \t\xa0"


def normalize_doc_defaults_spacing(
    doc, line_spacing: float, space_after_pt: float, details: list[str],
) -> bool:
    """Force ``<w:docDefaults>/<w:pPrDefault>/<w:pPr>/<w:spacing>`` to body values.

    Word's default ``pPrDefault`` from a fresh template typically declares
    ``after="200" line="276"`` (10 pt below every paragraph and ~1.15 line
    height). Empty paragraphs inherit those defaults regardless of any
    paragraph-level normalization that autofix performs only on non-empty
    text. The accumulated 10 pt blocks at section ends produce the visible
    «extra spacing after text» the customer reported. Rewriting the document
    defaults removes the gap once for the whole document and keeps non-empty
    paragraphs unchanged because they still carry their own explicit
    ``<w:spacing>`` overrides set by the rest of autofix.
    """
    from docx.oxml import OxmlElement

    doc_defaults = doc.styles.element.find(qn("w:docDefaults"))
    if doc_defaults is None:
        return False
    pPrDefault = doc_defaults.find(qn("w:pPrDefault"))
    if pPrDefault is None:
        pPrDefault = OxmlElement("w:pPrDefault")
        doc_defaults.append(pPrDefault)
    pPr = pPrDefault.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        pPrDefault.append(pPr)
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)

    target_after = str(int(round(space_after_pt * 20)))
    target_line = str(int(round(line_spacing * 240)))

    changed = False
    if spacing.get(qn("w:after")) != target_after:
        spacing.set(qn("w:after"), target_after)
        changed = True
    if spacing.get(qn("w:line")) != target_line:
        spacing.set(qn("w:line"), target_line)
        changed = True
    if spacing.get(qn("w:lineRule")) != "auto":
        spacing.set(qn("w:lineRule"), "auto")
        changed = True
    before_attr = spacing.get(qn("w:before"))
    if before_attr is not None and before_attr != "0":
        spacing.set(qn("w:before"), "0")
        changed = True

    if changed:
        details.append(
            f"Стили: интервал по умолчанию -> {line_spacing}, "
            f"после абзаца {space_after_pt} пт"
        )
    return changed


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


_SOURCE_LINE_RE = re.compile(r"^источник", re.IGNORECASE)


def normalize_title_page_spacing(doc, body_start: int, details: list[str]) -> bool:
    """Reduce excessive spacing on title page so it fits on one page."""
    changed = False
    for i in range(body_start):
        p = doc.paragraphs[i]
        pf = p.paragraph_format
        sa = pf.space_after
        if sa is not None and sa.pt > 12:
            pf.space_after = Pt(0)
            changed = True
        sb = pf.space_before
        if sb is not None and sb.pt > 12:
            pf.space_before = Pt(0)
            changed = True
        ls = pf.line_spacing
        if ls is not None and isinstance(ls, float) and ls < 1.0:
            pf.line_spacing = 1.0
            changed = True
    if changed:
        details.append("Титульный лист: убраны лишние отступы/интервалы")
    return changed


def normalize_source_line_spacing(doc, details: list[str]) -> bool:
    """Set single (1.0) line spacing on 'Источник:...' paragraphs under tables."""
    changed = False
    count = 0
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if _SOURCE_LINE_RE.match(text):
            pf = p.paragraph_format
            cur_ls = pf.line_spacing
            if cur_ls is None or abs(float(cur_ls) - 1.0) > 0.05:
                pf.line_spacing = 1.0
                changed = True
                count += 1
    if changed:
        details.append(f"«Источник…»: одинарный интервал ({count} шт.)")
    return changed
