from __future__ import annotations

from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn


def walk_style_pPr(paragraph):
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is not None:
        yield pPr
    style = paragraph.style
    while style is not None:
        try:
            spPr = style._element.find(qn("w:pPr"))
            if spPr is not None:
                yield spPr
            style = style.base_style
        except (AttributeError, TypeError):
            break


_JC_MAP = {
    "left": WD_PARAGRAPH_ALIGNMENT.LEFT,
    "start": WD_PARAGRAPH_ALIGNMENT.LEFT,
    "center": WD_PARAGRAPH_ALIGNMENT.CENTER,
    "right": WD_PARAGRAPH_ALIGNMENT.RIGHT,
    "end": WD_PARAGRAPH_ALIGNMENT.RIGHT,
    "both": WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
    "justify": WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
}


def effective_alignment(paragraph) -> WD_PARAGRAPH_ALIGNMENT | None:
    if paragraph.alignment is not None:
        return paragraph.alignment
    for pPr in walk_style_pPr(paragraph):
        jc = pPr.find(qn("w:jc"))
        if jc is not None:
            val = jc.get(qn("w:val"))
            if val in _JC_MAP:
                return _JC_MAP[val]
    return None


def effective_line_spacing(paragraph) -> float | None:
    pf = paragraph.paragraph_format
    raw = pf.line_spacing
    if raw is not None:
        if isinstance(raw, (int, float)):
            return float(raw)
        return None
    for pPr in walk_style_pPr(paragraph):
        spacing = pPr.find(qn("w:spacing"))
        if spacing is not None:
            line_val = spacing.get(qn("w:line"))
            if line_val is not None:
                line_rule = spacing.get(qn("w:lineRule"))
                if line_rule in (None, "auto"):
                    return int(line_val) / 240.0
                return None
    return 1.0


def effective_first_line_indent_mm(paragraph) -> float:
    pf = paragraph.paragraph_format
    if pf.first_line_indent is not None:
        return round(float(pf.first_line_indent.mm), 2)
    for pPr in walk_style_pPr(paragraph):
        ind = pPr.find(qn("w:ind"))
        if ind is not None:
            fl = ind.get(qn("w:firstLine"))
            if fl is not None:
                return round(int(fl) * 25.4 / 1440.0, 2)
    return 0.0


def effective_space_before_pt(paragraph) -> float:
    pf = paragraph.paragraph_format
    if pf.space_before is not None:
        return float(pf.space_before.pt)
    for pPr in walk_style_pPr(paragraph):
        spacing = pPr.find(qn("w:spacing"))
        if spacing is not None:
            val = spacing.get(qn("w:before"))
            if val is not None:
                return int(val) / 20.0
    return 0.0


def effective_space_after_pt(paragraph) -> float:
    pf = paragraph.paragraph_format
    if pf.space_after is not None:
        return float(pf.space_after.pt)
    for pPr in walk_style_pPr(paragraph):
        spacing = pPr.find(qn("w:spacing"))
        if spacing is not None:
            val = spacing.get(qn("w:after"))
            if val is not None:
                return int(val) / 20.0
    return 0.0


def _walk_style_rPr(run, paragraph):
    char_style = getattr(run, "style", None)
    while char_style is not None:
        try:
            srPr = char_style._element.find(qn("w:rPr"))
            if srPr is not None:
                yield srPr
            char_style = char_style.base_style
        except (AttributeError, TypeError):
            break
    style = paragraph.style
    while style is not None:
        try:
            srPr = style._element.find(qn("w:rPr"))
            if srPr is not None:
                yield srPr
            style = style.base_style
        except (AttributeError, TypeError):
            break


def effective_font_name(run, paragraph) -> str | None:
    if run.font.name is not None:
        return run.font.name
    for rPr in _walk_style_rPr(run, paragraph):
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is not None:
            for attr in ("w:ascii", "w:hAnsi"):
                val = rFonts.get(qn(attr))
                if val:
                    return val
    return None


def effective_font_size_pt(run, paragraph) -> float | None:
    if run.font.size is not None:
        return float(run.font.size.pt)
    for rPr in _walk_style_rPr(run, paragraph):
        sz = rPr.find(qn("w:sz"))
        if sz is not None:
            val = sz.get(qn("w:val"))
            if val:
                return float(val) / 2.0
    return None
