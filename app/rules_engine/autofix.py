from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from lxml import etree

from app.rules_engine.findings import Finding

logger = logging.getLogger(__name__)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_HEADING_STYLE_IDS = frozenset(
    {f"Heading{i}" for i in range(1, 10)}
)
_SKIP_STYLE_IDS = frozenset(
    {f"TOC{i}" for i in range(1, 10)}
    | {"TOCHeading", "TableofFigures", "TableofAuthorities", "Caption", "Title",
       "Subtitle", "NoSpacing", "BalloonText", "MacroText", "EndnoteText",
       "FootnoteText", "Header", "Footer", "CommentText"}
)
_SKIP_STYLE_NAMES = frozenset({
    "toc heading", "table of figures", "table of authorities", "caption",
    "title", "subtitle", "no spacing", "balloon text", "macro text",
    "endnote text", "footnote text", "header", "footer", "annotation text",
})
_SKIP_NAME_PREFIXES = ("toc ", "toc\xa0", "index ")
_LIST_STYLE_IDS = frozenset({
    "ListParagraph", "ListBullet", "ListBullet2", "ListBullet3",
    "ListNumber", "ListNumber2", "ListNumber3",
    "ListContinue", "ListContinue2", "ListContinue3",
})
_LIST_STYLE_NAMES = frozenset({
    "list paragraph", "list bullet", "list bullet 2", "list bullet 3",
    "list number", "list number 2", "list number 3",
    "list continue", "list continue 2", "list continue 3",
})

_BINARY_PREFIXES = ("word/media/", "word/embeddings/")


def _walk_style_pPr(paragraph):
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


def _is_heading_para(paragraph) -> bool:
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _HEADING_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    if "heading" in sname or "\u0437\u0430\u0433\u043e\u043b\u043e\u0432" in sname:
        return True
    for pPr in _walk_style_pPr(paragraph):
        ol = pPr.find(qn("w:outlineLvl"))
        if ol is not None:
            val = ol.get(qn("w:val"))
            try:
                if val is not None and int(val) < 9:
                    return True
            except (TypeError, ValueError):
                pass
    return False


def _should_skip_para(paragraph) -> bool:
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _SKIP_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    if sname in _SKIP_STYLE_NAMES:
        return True
    return any(sname.startswith(p) for p in _SKIP_NAME_PREFIXES)


def _is_list_para(paragraph) -> bool:
    for pPr in _walk_style_pPr(paragraph):
        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            numId = numPr.find(qn("w:numId"))
            if numId is not None and numId.get(qn("w:val")) != "0":
                return True
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _LIST_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    return sname in _LIST_STYLE_NAMES


def _is_field_code_run(run) -> bool:
    elem = run._element
    return (
        elem.find(qn("w:fldChar")) is not None
        or elem.find(qn("w:instrText")) is not None
    )


@dataclass(slots=True)
class AutoFixResult:
    output_file_path: str | None
    details: list[str]


def apply_safe_autofixes(
    file_path: str, rules: dict | None, findings: list[Finding],
) -> AutoFixResult:
    source = Path(file_path)
    if source.suffix.lower() != ".docx" or not source.exists():
        return AutoFixResult(output_file_path=None, details=[])

    cfg = _AutoFixConfig.from_rules(rules)
    if not cfg.enabled:
        return AutoFixResult(output_file_path=None, details=[])

    try:
        doc = Document(str(source))
    except Exception:
        logger.warning("Autofix: cannot open DOCX %s", file_path)
        return AutoFixResult(output_file_path=None, details=[])

    changed = False
    details: list[str] = []

    if cfg.normalize_margins:
        for sec_idx, section in enumerate(doc.sections):
            if _fix_section_margins(section, cfg.margins_mm, sec_idx, details):
                changed = True

    for idx, paragraph in enumerate(doc.paragraphs):
        text = (paragraph.text or "").strip()
        if not text:
            continue

        if _is_heading_para(paragraph):
            if cfg.normalize_headings:
                if _fix_heading(paragraph, idx, cfg, details):
                    changed = True
            continue

        if _should_skip_para(paragraph):
            continue

        is_list = _is_list_para(paragraph)
        pf = paragraph.paragraph_format

        if not is_list and cfg.normalize_alignment and paragraph.alignment != WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            changed = True
            details.append(f"Paragraph #{idx + 1}: alignment justify")

        if cfg.normalize_line_spacing:
            curr = pf.line_spacing
            needs_fix = True
            if isinstance(curr, (int, float)):
                needs_fix = abs(float(curr) - cfg.line_spacing) > 0.05
            if needs_fix:
                pf.line_spacing = cfg.line_spacing
                changed = True
                details.append(f"Paragraph #{idx + 1}: line spacing {cfg.line_spacing}")

        if not is_list and cfg.normalize_first_line_indent:
            curr_mm = None
            if pf.first_line_indent is not None:
                curr_mm = round(float(pf.first_line_indent.mm), 2)
            if curr_mm is None or abs(curr_mm - cfg.first_line_indent_mm) > 0.5:
                pf.first_line_indent = Mm(cfg.first_line_indent_mm)
                changed = True
                details.append(f"Paragraph #{idx + 1}: first line indent {cfg.first_line_indent_mm} mm")

        if not is_list and cfg.normalize_spacing_before_after:
            if pf.space_before is None or abs(float(pf.space_before.pt) - cfg.space_before_pt) > 0.2:
                pf.space_before = Pt(cfg.space_before_pt)
                changed = True
                details.append(f"Paragraph #{idx + 1}: spacing before {cfg.space_before_pt} pt")
            if pf.space_after is None or abs(float(pf.space_after.pt) - cfg.space_after_pt) > 0.2:
                pf.space_after = Pt(cfg.space_after_pt)
                changed = True
                details.append(f"Paragraph #{idx + 1}: spacing after {cfg.space_after_pt} pt")

        if cfg.normalize_font:
            font_changed = False
            for run in paragraph.runs:
                if _is_field_code_run(run):
                    continue
                if cfg.font_name and run.font.name != cfg.font_name:
                    run.font.name = cfg.font_name
                    font_changed = True
                size_pt = float(run.font.size.pt) if run.font.size else None
                if size_pt is None or abs(size_pt - cfg.font_size_pt) > 0.2:
                    run.font.size = Pt(cfg.font_size_pt)
                    font_changed = True
            if font_changed:
                changed = True
                details.append(f"Paragraph #{idx + 1}: font {cfg.font_name}, {cfg.font_size_pt}pt")

    if cfg.normalize_table_width and _clamp_overflow_table_widths(doc, details):
        changed = True

    if not changed:
        return AutoFixResult(output_file_path=None, details=[])

    output = source.with_name(f"{source.stem}.fixed.docx")
    try:
        doc.save(str(output))
    except Exception:
        logger.exception("Autofix: failed to save fixed DOCX to %s", output)
        return AutoFixResult(output_file_path=None, details=[])

    try:
        _postprocess_fixed_docx(source, output)
    except Exception:
        logger.warning("Autofix: postprocessing failed for %s, using python-docx output", output)

    findings.append(
        Finding(
            title="Автоисправления",
            category="autofix",
            severity="advice",
            expected="Только безопасные изменения форматирования",
            found="Применены безопасные автоисправления",
            location="документ",
            recommendation="Скачайте исправленный DOCX",
            auto_fixed=True,
            auto_fix_details="; ".join(details[:30]),
        )
    )

    return AutoFixResult(output_file_path=str(output), details=details)


def _postprocess_fixed_docx(original: Path, output: Path) -> None:
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


def _min_content_width_twips(doc: Document) -> int:
    widths: list[int] = []
    for sec in doc.sections:
        try:
            inner = sec.page_width.twips - sec.left_margin.twips - sec.right_margin.twips
            widths.append(max(int(inner), 400))
        except (AttributeError, TypeError, ValueError):
            continue
    return min(widths) if widths else 8640


def _set_table_width_pct100(tbl) -> None:
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)
    for old in tbl_pr.findall(qn("w:tblW")):
        tbl_pr.remove(old)
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:w"), "5000")
    tbl_w.set(qn("w:type"), "pct")
    tbl_pr.append(tbl_w)


def _clamp_overflow_table_widths(doc: Document, details: list[str]) -> bool:
    limit = _min_content_width_twips(doc)
    slop_twips = 72
    changed_any = False
    seen: set[int] = set()
    for table in doc.tables:
        el = table._tbl
        tid = id(el)
        if tid in seen:
            continue
        seen.add(tid)
        tbl_pr = el.tblPr
        if tbl_pr is None:
            continue
        tbl_w = tbl_pr.find(qn("w:tblW"))
        if tbl_w is None:
            continue
        if tbl_w.get(qn("w:type")) != "dxa":
            continue
        w_raw = tbl_w.get(qn("w:w"))
        try:
            w_val = int(w_raw) if w_raw is not None else 0
        except (TypeError, ValueError):
            continue
        if w_val <= limit + slop_twips:
            continue
        _set_table_width_pct100(el)
        changed_any = True
    if changed_any:
        details.append("Tables: width clamped to text area (100%)")
    return changed_any


def _fix_section_margins(
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


def _fix_heading(paragraph, idx: int, cfg: "_AutoFixConfig", details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if _is_field_code_run(run):
            continue
        if cfg.heading_font and run.font.name != cfg.heading_font:
            run.font.name = cfg.heading_font
            changed = True
        size_pt = float(run.font.size.pt) if run.font.size else None
        if size_pt is None or abs(size_pt - cfg.heading_size_pt) > 0.2:
            run.font.size = Pt(cfg.heading_size_pt)
            changed = True
        if cfg.heading_bold and not run.bold:
            run.bold = True
            changed = True
    if changed:
        details.append(
            f"Heading #{idx + 1}: {cfg.heading_font}, {cfg.heading_size_pt}pt, bold"
        )
    return changed


@dataclass(slots=True)
class _AutoFixConfig:
    enabled: bool
    normalize_alignment: bool
    normalize_line_spacing: bool
    normalize_first_line_indent: bool
    normalize_spacing_before_after: bool
    normalize_font: bool
    normalize_margins: bool
    normalize_headings: bool
    normalize_table_width: bool
    line_spacing: float
    first_line_indent_mm: float
    space_before_pt: float
    space_after_pt: float
    font_name: str
    font_size_pt: float
    margins_mm: dict
    heading_font: str
    heading_size_pt: float
    heading_bold: bool

    @classmethod
    def from_rules(cls, rules: dict | None) -> "_AutoFixConfig":
        blocks = {
            str(b.get("key")): b
            for b in (rules or {}).get("blocks", [])
            if isinstance(b, dict)
        }
        auto = blocks.get("autofix", {})
        params = auto.get("params") or {}
        enabled = bool(auto.get("enabled", True))

        typography = blocks.get("typography", {})
        body = (typography.get("params") or {}).get("body") or {}

        layout = blocks.get("layout", {})
        layout_params = layout.get("params") or {}

        heading = blocks.get("heading_formatting", {})
        heading_params = heading.get("params") or {}

        return cls(
            enabled=enabled,
            normalize_alignment=bool(params.get("normalize_alignment", True)),
            normalize_line_spacing=bool(params.get("normalize_line_spacing", True)),
            normalize_first_line_indent=bool(params.get("normalize_first_line_indent", True)),
            normalize_spacing_before_after=bool(params.get("normalize_spacing_before_after", True)),
            normalize_font=bool(params.get("normalize_font", True)),
            normalize_margins=bool(params.get("normalize_margins", True)),
            normalize_headings=bool(params.get("normalize_headings", True)),
            normalize_table_width=bool(params.get("normalize_table_width", True)),
            line_spacing=float(body.get("line_spacing", 1.5)),
            first_line_indent_mm=float(body.get("first_line_indent_mm", 12.5)),
            space_before_pt=float(params.get("space_before_pt", 0)),
            space_after_pt=float(params.get("space_after_pt", 0)),
            font_name=str(body.get("font", "Times New Roman")),
            font_size_pt=float(body.get("size_pt", 14)),
            margins_mm=layout_params.get(
                "margins_mm", {"left": 30, "right": 15, "top": 20, "bottom": 25},
            ),
            heading_font=str(heading_params.get("font", body.get("font", "Times New Roman"))),
            heading_size_pt=float(heading_params.get("size_pt", body.get("size_pt", 14))),
            heading_bold=bool(heading_params.get("require_bold", True)),
        )
