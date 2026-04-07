from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, RGBColor
from lxml import etree

from app.rules_engine.style_resolve import effective_first_line_indent_mm

logger = logging.getLogger(__name__)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_BINARY_PREFIXES = ("word/media/", "word/embeddings/")

_BULLET_CHARS = frozenset("\u2022\u25cf\u25cb\u25e6\u2023\u2043\u25aa\u25ab")
_EM_DASH = "\u2014"
_EN_DASH = "\u2013"
_HYPHEN = "-"
_BLACK = RGBColor(0, 0, 0)

_CAPTION_RE = re.compile(
    r"^(?:"
    r"\u0420\u0438\u0441\u0443\u043d\u043e\u043a"
    r"|\u0420\u0438\u0441\.?"
    r"|\u0422\u0430\u0431\u043b\u0438\u0446\u0430"
    r")\s+\d+"
)


def is_field_code_run(run) -> bool:
    elem = run._element
    return (
        elem.find(qn("w:fldChar")) is not None
        or elem.find(qn("w:instrText")) is not None
    )


def is_manual_list_para(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped:
        return False
    if stripped[0] in _BULLET_CHARS:
        return True
    if stripped[0] in (_HYPHEN, _EN_DASH, _EM_DASH) and len(stripped) > 1:
        if not stripped[1].isdigit():
            return True
    return False


def fix_font_color_styles(doc: Document, details: list[str]) -> bool:
    changed = False
    for style in doc.styles:
        name = (getattr(style, "name", "") or "").lower()
        if not any(k in name for k in (
            "hyperlink", "heading", "toc",
            "\u0437\u0430\u0433\u043e\u043b\u043e\u0432",
        )):
            continue
        try:
            c = style.font.color
            if (c.rgb is not None and c.rgb != _BLACK) or c.theme_color is not None:
                c.rgb = _BLACK
                changed = True
        except (AttributeError, TypeError):
            pass
    if changed:
        details.append("Styles: font color -> black")
    return changed


def fix_font_color_runs(paragraph, idx: int, details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run):
            continue
        try:
            c = run.font.color
            if c.rgb is not None and c.rgb != _BLACK:
                c.rgb = _BLACK
                changed = True
            elif c.theme_color is not None:
                c.rgb = _BLACK
                changed = True
        except (AttributeError, TypeError):
            pass
    if changed:
        details.append(f"Paragraph #{idx + 1}: font color -> black")
    return changed


def fix_italic_styles(doc: Document, details: list[str]) -> bool:
    changed = False
    for style in doc.styles:
        try:
            if style.font.italic is True:
                style.font.italic = False
                changed = True
        except (AttributeError, TypeError):
            pass
    if changed:
        details.append("Styles: italic removed")
    return changed


def fix_remove_italic(paragraph, idx: int, details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run):
            continue
        if run.italic:
            run.italic = False
            changed = True
    if changed:
        details.append(f"Paragraph #{idx + 1}: italic removed")
    return changed


def fix_list_indent(paragraph, idx: int, details: list[str]) -> bool:
    eff = effective_first_line_indent_mm(paragraph)
    if abs(eff) < 0.5:
        return False
    paragraph.paragraph_format.first_line_indent = Mm(0)
    details.append(f"Paragraph #{idx + 1}: list indent zeroed")
    return True


_ALL_MARKER_CHARS = _BULLET_CHARS | frozenset((_EN_DASH, _EM_DASH))


def fix_markers_text(paragraph, idx: int, details: list[str]) -> bool:
    if not paragraph.runs:
        return False
    full = paragraph.text.lstrip()
    if not full or full[0] not in _ALL_MARKER_CHARS:
        return False
    for run in paragraph.runs:
        rt = run.text
        if not rt.strip():
            continue
        stripped = rt.lstrip()
        if stripped and stripped[0] in _ALL_MARKER_CHARS:
            ws = rt[: len(rt) - len(stripped)]
            rest = stripped[1:].lstrip()
            run.text = ws + _HYPHEN + " " + rest
            details.append(f"Paragraph #{idx + 1}: marker -> dash")
            return True
        break
    return False


def fix_numbering_bullets(
    doc: Document, body_font: str, details: list[str],
) -> bool:
    try:
        npart = doc.part.numbering_part
    except Exception:
        return False
    if npart is None:
        return False
    elem = npart._element
    changed = False
    for lvl in elem.iter(qn("w:lvl")):
        fmt = lvl.find(qn("w:numFmt"))
        if fmt is None or fmt.get(qn("w:val")) != "bullet":
            continue
        lt = lvl.find(qn("w:lvlText"))
        if lt is None:
            continue
        val = lt.get(qn("w:val")) or ""
        if val and val != _HYPHEN:
            lt.set(qn("w:val"), _HYPHEN)
            rPr = lvl.find(qn("w:rPr"))
            if rPr is not None:
                rFonts = rPr.find(qn("w:rFonts"))
                if rFonts is not None:
                    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                        fq = qn(a)
                        if rFonts.get(fq) is not None:
                            rFonts.set(fq, body_font)
            changed = True
    if changed:
        details.append("Numbering: bullet markers -> dash")
    return changed


def fix_dashes_in_text(paragraph, idx: int, details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run):
            continue
        t = run.text
        if _EM_DASH in t or _EN_DASH in t:
            run.text = t.replace(_EM_DASH, _HYPHEN).replace(_EN_DASH, _HYPHEN)
            changed = True
    if changed:
        details.append(f"Paragraph #{idx + 1}: long dashes -> short")
    return changed


def fix_caption_trailing_dot(paragraph, idx: int, details: list[str]) -> bool:
    text = paragraph.text.strip()
    if not text.endswith(".") or text.endswith(".."):
        return False
    if not _CAPTION_RE.match(text):
        return False
    for run in reversed(paragraph.runs):
        rt = run.text
        s = rt.rstrip()
        if s and s.endswith(".") and not s.endswith(".."):
            run.text = s[:-1] + rt[len(s):]
            details.append(f"Paragraph #{idx + 1}: caption trailing dot removed")
            return True
        if s:
            break
    return False


def postprocess_fixed_docx(original: Path, output: Path) -> None:
    orig_bins: dict[str, tuple[zipfile.ZipInfo, bytes]] = {}
    with zipfile.ZipFile(str(original), "r") as orig_zf:
        for info in orig_zf.infolist():
            if any(info.filename.startswith(p) for p in _BINARY_PREFIXES) and not info.filename.endswith("/"):
                orig_bins[info.filename] = (info, orig_zf.read(info.filename))

    has_toc = _zip_has_toc(output)

    if not orig_bins and not has_toc:
        _validate_docx_zip(output)
        return

    temp_path = output.with_name(output.stem + ".tmp.docx")
    settings_injected = False
    with zipfile.ZipFile(str(output), "r") as out_zf:
        with zipfile.ZipFile(str(temp_path), "w", zipfile.ZIP_DEFLATED) as new_zf:
            for item in out_zf.infolist():
                if item.filename in orig_bins:
                    orig_info, orig_data = orig_bins[item.filename]
                    restored = _clone_zipinfo(orig_info)
                    restored.compress_type = zipfile.ZIP_STORED
                    new_zf.writestr(restored, orig_data)
                elif has_toc and item.filename == "word/settings.xml":
                    data = _inject_update_fields(out_zf.read(item.filename))
                    new_zf.writestr(item, data)
                    settings_injected = True
                else:
                    new_zf.writestr(item, out_zf.read(item.filename))

    if has_toc and not settings_injected:
        logger.debug("Autofix: word/settings.xml not found, cannot inject updateFields")

    _validate_docx_zip(temp_path)
    temp_path.replace(output)


def _zip_has_toc(path: Path) -> bool:
    with zipfile.ZipFile(str(path), "r") as zf:
        if "word/document.xml" not in zf.namelist():
            return False
        data = zf.read("word/document.xml")
        return b"TOC " in data or b"Table of Contents" in data


def _clone_zipinfo(src: zipfile.ZipInfo) -> zipfile.ZipInfo:
    zi = zipfile.ZipInfo(src.filename)
    zi.date_time = src.date_time
    zi.compress_type = src.compress_type
    zi.comment = src.comment
    zi.extra = src.extra
    zi.create_system = src.create_system
    zi.external_attr = src.external_attr
    zi.flag_bits = src.flag_bits & 0x800
    return zi


def _inject_update_fields(settings_bytes: bytes) -> bytes:
    root = etree.fromstring(settings_bytes)
    tag = f"{{{_W_NS}}}updateFields"
    existing = root.find(tag)
    if existing is None:
        elem = etree.SubElement(root, tag)
        elem.set(f"{{{_W_NS}}}val", "true")
    else:
        existing.set(f"{{{_W_NS}}}val", "true")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _validate_docx_zip(path: Path) -> None:
    with zipfile.ZipFile(str(path), "r") as zf:
        bad = zf.testzip()
        if bad is not None:
            raise ValueError(f"Corrupted ZIP entry: {bad}")
        names = set(zf.namelist())
        for required in ("[Content_Types].xml", "word/document.xml"):
            if required not in names:
                raise ValueError(f"Missing required entry: {required}")
        etree.fromstring(zf.read("word/document.xml"))
        if "word/settings.xml" in names:
            etree.fromstring(zf.read("word/settings.xml"))


def preflight_margins_safe(doc: Document, target_margins_mm: dict) -> bool:
    mn = None
    for sec in doc.sections:
        try:
            pw = sec.page_width.twips
        except (AttributeError, TypeError):
            continue
        lt = Mm(target_margins_mm.get("left", 30)).twips
        rt = Mm(target_margins_mm.get("right", 15)).twips
        content = pw - lt - rt
        if mn is None or content < mn:
            mn = content

    if mn is None or mn < 400:
        return False

    slop = 72
    for table in doc.tables:
        el = table._tbl
        tp = el.tblPr
        if tp is None:
            continue
        tw = tp.find(qn("w:tblW"))
        if tw is None:
            continue
        if tw.get(qn("w:type")) != "dxa":
            continue
        wr = tw.get(qn("w:w"))
        try:
            wv = int(wr) if wr is not None else 0
        except (TypeError, ValueError):
            continue
        if wv > mn + slop:
            return False

    return True


def set_table_width_pct100(tbl) -> None:
    tp = tbl.tblPr
    if tp is None:
        tp = OxmlElement("w:tblPr")
        tbl.insert(0, tp)
    for old in tp.findall(qn("w:tblW")):
        tp.remove(old)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), "5000")
    tw.set(qn("w:type"), "pct")
    tp.append(tw)


def clamp_overflow_table_widths(doc: Document, details: list[str]) -> bool:
    limit = min_content_width_twips(doc)
    slop = 72
    changed_any = False
    seen: set[int] = set()
    for table in doc.tables:
        el = table._tbl
        tid = id(el)
        if tid in seen:
            continue
        seen.add(tid)
        tp = el.tblPr
        if tp is None:
            continue
        tw = tp.find(qn("w:tblW"))
        if tw is None:
            continue
        if tw.get(qn("w:type")) != "dxa":
            continue
        wr = tw.get(qn("w:w"))
        try:
            wv = int(wr) if wr is not None else 0
        except (TypeError, ValueError):
            continue
        if wv <= limit + slop:
            continue
        set_table_width_pct100(el)
        changed_any = True
    if changed_any:
        details.append("Tables: width clamped to text area (100%)")
    return changed_any


def min_content_width_twips(doc: Document) -> int:
    widths: list[int] = []
    for sec in doc.sections:
        try:
            inner = sec.page_width.twips - sec.left_margin.twips - sec.right_margin.twips
            widths.append(max(int(inner), 400))
        except (AttributeError, TypeError, ValueError):
            continue
    return min(widths) if widths else 8640


def fix_section_margins(
    section, margins_mm: dict, sec_idx: int, details: list[str],
) -> bool:
    changed = False
    for key in ("left", "right", "top", "bottom"):
        target_mm = margins_mm.get(key)
        if target_mm is None:
            continue
        attr = f"{key}_margin"
        current = getattr(section, attr, None)
        target = Mm(target_mm)
        if current is None or abs(int(current) - int(target)) > int(Mm(0.5)):
            setattr(section, attr, target)
            changed = True
    if changed:
        details.append(f"Section #{sec_idx + 1}: margins fixed")
    return changed
