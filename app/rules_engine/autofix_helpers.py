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

_BULLET_CHARS = frozenset("\u2022\u25cf\u25cb\u25e6\u2023\u2043\u25aa\u25ab\u00b7")
_EM_DASH = "\u2014"
_EN_DASH = "\u2013"
_HYPHEN = "-"
_BLACK = RGBColor(0, 0, 0)

_ENUM_LETTER_RE = re.compile(r"^[а-яёa-z]\)\s", re.IGNORECASE)
_ENUM_DIGIT_PAREN_RE = re.compile(r"^\d{1,2}\)\s")

_CAPTION_RE = re.compile(
    r"^(?:"
    r"\u0420\u0438\u0441\u0443\u043d\u043e\u043a"
    r"|\u0420\u0438\u0441\.?"
    r"|\u0422\u0430\u0431\u043b\u0438\u0446\u0430"
    r")\s+\d+"
)
_THEME_COLOR_ATTRS = (qn("w:themeColor"), qn("w:themeTint"), qn("w:themeShade"))

def _set_color_to_black(color_el) -> bool:
    val = color_el.get(qn("w:val"))
    needs_fix = (val and val.lower() != "000000") or color_el.get(qn("w:themeColor")) is not None
    if not needs_fix:
        return False
    color_el.set(qn("w:val"), "000000")
    for attr in _THEME_COLOR_ATTRS:
        if color_el.get(attr) is not None:
            del color_el.attrib[attr]
    return True

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
    if stripped[0] == "*" and len(stripped) > 1 and stripped[1] in (" ", "\t", "\xa0"):
        return True
    if stripped[0] in (_HYPHEN, _EN_DASH, _EM_DASH) and len(stripped) > 1:
        if not stripped[1].isdigit():
            return True
    if _ENUM_LETTER_RE.match(stripped) or _ENUM_DIGIT_PAREN_RE.match(stripped):
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
        details.append("\u0421\u0442\u0438\u043b\u0438: \u0446\u0432\u0435\u0442 \u0448\u0440\u0438\u0444\u0442\u0430 -> \u0447\u0451\u0440\u043d\u044b\u0439")
    return changed

def fix_font_color_runs(paragraph, para_label: str, details: list[str]) -> bool:
    p_elem = paragraph._element
    changed = False
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is not None:
        rPr_def = pPr.find(qn("w:rPr"))
        if rPr_def is not None:
            c_el = rPr_def.find(qn("w:color"))
            if c_el is not None and _set_color_to_black(c_el):
                changed = True
    for r_elem in p_elem.iter(qn("w:r")):
        rPr = r_elem.find(qn("w:rPr"))
        if rPr is None:
            continue
        c_el = rPr.find(qn("w:color"))
        if c_el is not None and _set_color_to_black(c_el):
            changed = True
    if changed:
        details.append(f"{para_label}: \u0446\u0432\u0435\u0442 \u0448\u0440\u0438\u0444\u0442\u0430 -> \u0447\u0451\u0440\u043d\u044b\u0439")
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
        details.append("\u0421\u0442\u0438\u043b\u0438: \u043a\u0443\u0440\u0441\u0438\u0432 \u0443\u0431\u0440\u0430\u043d")
    return changed

def fix_remove_italic(paragraph, para_label: str, details: list[str]) -> bool:
    p_elem = paragraph._element
    changed = False
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is not None:
        rPr_default = pPr.find(qn("w:rPr"))
        if rPr_default is not None:
            for tag in (qn("w:i"), qn("w:iCs")):
                el = rPr_default.find(tag)
                if el is not None:
                    rPr_default.remove(el)
                    changed = True
    for r_elem in p_elem.iter(qn("w:r")):
        rPr = r_elem.find(qn("w:rPr"))
        if rPr is None:
            continue
        for tag in (qn("w:i"), qn("w:iCs")):
            el = rPr.find(tag)
            if el is not None:
                rPr.remove(el)
                changed = True
    if changed:
        details.append(f"{para_label}: \u043a\u0443\u0440\u0441\u0438\u0432 \u0443\u0431\u0440\u0430\u043d")
    return changed

def fix_list_indent(paragraph, para_label: str, details: list[str]) -> bool:
    pf = paragraph.paragraph_format
    changed = False
    if abs(effective_first_line_indent_mm(paragraph)) > 0.5:
        pf.first_line_indent = Mm(0)
        changed = True
    if pf.left_indent is not None and int(pf.left_indent) > int(Mm(0.5)):
        pf.left_indent = Mm(0)
        changed = True
    pPr_el = paragraph._element.find(qn("w:pPr"))
    if pPr_el is not None:
        ind = pPr_el.find(qn("w:ind"))
        if ind is not None:
            for a in (qn("w:left"), qn("w:start"), qn("w:hanging")):
                v = ind.get(a)
                if v is None:
                    continue
                try:
                    if int(v) > 0:
                        if a == qn("w:hanging"):
                            ind.attrib.pop(a, None)
                        else:
                            ind.set(a, "0")
                        changed = True
                except (ValueError, TypeError):
                    pass
    if changed:
        details.append(f"{para_label}: \u043e\u0442\u0441\u0442\u0443\u043f \u0441\u043f\u0438\u0441\u043a\u0430 \u043e\u0431\u043d\u0443\u043b\u0451\u043d")
    return changed

_ALL_MARKER_CHARS = _BULLET_CHARS | frozenset((_EN_DASH, _EM_DASH, "*"))

def fix_markers_text(
    paragraph, para_label: str, details: list[str],
    marker_char: str = _HYPHEN,
) -> bool:
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
            new_text = ws + marker_char + " " + rest
            if new_text == rt:
                return False
            run.text = new_text
            details.append(f"{para_label}: \u043c\u0430\u0440\u043a\u0435\u0440 -> {marker_char}")
            return True
        break
    return False

def fix_numbering_bullets(
    doc: Document, body_font: str, details: list[str],
    marker_char: str = _HYPHEN,
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
        if val and val != marker_char:
            lt.set(qn("w:val"), marker_char)
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
        details.append("\u041d\u0443\u043c\u0435\u0440\u0430\u0446\u0438\u044f: \u043c\u0430\u0440\u043a\u0435\u0440\u044b -> \u0434\u0435\u0444\u0438\u0441")
    return changed

def fix_dashes_in_text(paragraph, para_label: str, details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run):
            continue
        t = run.text
        if _EM_DASH in t or _EN_DASH in t:
            run.text = t.replace(_EM_DASH, _HYPHEN).replace(_EN_DASH, _HYPHEN)
            changed = True
    if changed:
        details.append(f"{para_label}: \u0434\u043b\u0438\u043d\u043d\u044b\u0435 \u0442\u0438\u0440\u0435 -> \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0435")
    return changed

def fix_caption_trailing_dot(paragraph, para_label: str, details: list[str]) -> bool:
    text = paragraph.text.strip()
    if not text.endswith(".") or text.endswith(".."):
        return False
    if not _CAPTION_RE.match(text):
        return False
    t_elements = list(paragraph._element.iter(qn("w:t")))
    for t_el in reversed(t_elements):
        s = (t_el.text or "").rstrip()
        if s and s.endswith(".") and not s.endswith(".."):
            tail = (t_el.text or "")[len(s):]
            t_el.text = s[:-1] + tail
            details.append(f"{para_label}: \u0442\u043e\u0447\u043a\u0430 \u0432 \u043a\u043e\u043d\u0446\u0435 \u043f\u043e\u0434\u043f\u0438\u0441\u0438 \u0443\u0431\u0440\u0430\u043d\u0430")
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
    for a in ("date_time", "compress_type", "comment", "extra", "create_system", "external_attr"):
        setattr(zi, a, getattr(src, a))
    zi.flag_bits = src.flag_bits & 0x800
    return zi

def _inject_update_fields(settings_bytes: bytes) -> bytes:
    root = etree.fromstring(settings_bytes)
    tag = f"{{{_W_NS}}}updateFields"
    el = root.find(tag)
    if el is None:
        el = etree.SubElement(root, tag)
    el.set(f"{{{_W_NS}}}val", "true")
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
    lt = Mm(target_margins_mm.get("left", 30)).twips
    rt = Mm(target_margins_mm.get("right", 15)).twips
    mn = None
    for sec in doc.sections:
        try: pw = sec.page_width.twips
        except (AttributeError, TypeError): continue
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
        details.append("\u0422\u0430\u0431\u043b\u0438\u0446\u044b: \u0448\u0438\u0440\u0438\u043d\u0430 \u043f\u0440\u0438\u0432\u0435\u0434\u0435\u043d\u0430 \u043a \u043e\u0431\u043b\u0430\u0441\u0442\u0438 \u0442\u0435\u043a\u0441\u0442\u0430 (100%)")
    return changed_any

def min_content_width_twips(doc: Document) -> int:
    w = []
    for s in doc.sections:
        try: w.append(max(int(s.page_width.twips - s.left_margin.twips - s.right_margin.twips), 400))
        except (AttributeError, TypeError, ValueError): pass
    return min(w) if w else 8640

def iter_table_cell_paragraphs(doc: Document):
    def _collect(tbl, out):
        for row in tbl.rows:
            for cell in row.cells:
                out.extend(cell.paragraphs)
                for nested in cell.tables:
                    _collect(nested, out)
    all_paras: list = []
    for table in doc.tables:
        _collect(table, all_paras)
    seen: set[int] = set()
    for p in all_paras:
        eid = id(p._element)
        if eid not in seen:
            seen.add(eid)
            yield p

def fix_remove_highlight(paragraph, para_label: str, details: list[str]) -> bool:
    _HL, _SHD = qn("w:highlight"), qn("w:shd")
    _SAFE = ("", "auto", "ffffff")
    def _strip(parent):
        c = False
        for tag in (_HL, _SHD):
            el = parent.find(tag)
            if el is not None and (tag != _SHD or (el.get(qn("w:fill")) or "").lower() not in _SAFE):
                parent.remove(el); c = True
        return c
    changed = False
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is not None:
        changed |= _strip(pPr)
    for r in paragraph._element.iter(qn("w:r")):
        rPr = r.find(qn("w:rPr"))
        if rPr is not None:
            changed |= _strip(rPr)
    if changed:
        details.append(f"{para_label}: \u0437\u0430\u043b\u0438\u0432\u043a\u0430/\u0432\u044b\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u0443\u0431\u0440\u0430\u043d\u044b")
    return changed

def fix_remove_strange_chars(paragraph, para_label: str, details: list[str], allowed_re) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run) or not run.text:
            continue
        cleaned = "".join(c for c in run.text if allowed_re.match(c))
        if cleaned != run.text:
            run.text = cleaned
            changed = True
    if changed:
        for run in paragraph.runs:
            if is_field_code_run(run) or not run.text:
                continue
            stripped = run.text.lstrip()
            if stripped != run.text:
                run.text = stripped
            break
        details.append(f"{para_label}: \u043f\u043e\u0441\u0442\u043e\u0440\u043e\u043d\u043d\u0438\u0435 \u0441\u0438\u043c\u0432\u043e\u043b\u044b \u0443\u0431\u0440\u0430\u043d\u044b")
    return changed

def remove_manual_page_breaks(paragraph) -> bool:
    changed = False
    for br in list(paragraph._element.iter(qn("w:br"))):
        if br.get(qn("w:type")) == "page":
            br.getparent().remove(br)
            changed = True
    return changed

def fix_page_break_before(paragraph, para_label: str, details: list[str]) -> bool:
    pf = paragraph.paragraph_format
    if pf.page_break_before:
        return False
    pf.page_break_before = True
    details.append(f"{para_label}: \u0440\u0430\u0437\u0440\u044b\u0432 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d")
    return True

def _is_removable_empty_para(para) -> bool:
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

def remove_empty_paras_before_page_breaks(doc, details: list[str]) -> bool:
    paragraphs = list(doc.paragraphs)
    body = doc.element.body
    to_remove = []
    seen: set[int] = set()

    for i, para in enumerate(paragraphs):
        pf = para.paragraph_format
        if not pf.page_break_before:
            continue
        j = i - 1
        while j >= 0:
            prev = paragraphs[j]
            if not _is_removable_empty_para(prev):
                break
            eid = id(prev._element)
            if eid not in seen:
                seen.add(eid)
                to_remove.append(prev._element)
            j -= 1

    for elem in to_remove:
        body.remove(elem)

    if to_remove:
        details.append(f"\u0423\u0434\u0430\u043b\u0435\u043d\u043e {len(to_remove)} \u043f\u0443\u0441\u0442\u044b\u0445 \u0430\u0431\u0437\u0430\u0446\u0435\u0432 \u043f\u0435\u0440\u0435\u0434 \u0440\u0430\u0437\u0440\u044b\u0432\u0430\u043c\u0438 \u0441\u0442\u0440\u0430\u043d\u0438\u0446")
    return len(to_remove) > 0

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
        details.append(f"\u0421\u0435\u043a\u0446\u0438\u044f #{sec_idx + 1}: \u043f\u043e\u043b\u044f \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u044b")
    return changed
