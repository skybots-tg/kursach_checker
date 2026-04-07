from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

from app.rules_engine.autofix_helpers import (
    clamp_overflow_table_widths,
    fix_caption_trailing_dot,
    fix_dashes_in_text,
    fix_font_color_runs,
    fix_font_color_styles,
    fix_italic_styles,
    fix_list_indent,
    fix_markers_text,
    fix_numbering_bullets,
    fix_remove_italic,
    fix_section_margins,
    is_field_code_run,
    is_manual_list_para,
    postprocess_fixed_docx,
    preflight_margins_safe,
)
from app.rules_engine.findings import Finding
from app.rules_engine.style_resolve import (
    detect_toc_paragraph_indices,
    effective_alignment,
    effective_first_line_indent_mm,
    effective_font_name,
    effective_font_size_pt,
    effective_line_spacing,
    effective_space_after_pt,
    effective_space_before_pt,
    walk_style_pPr,
)

logger = logging.getLogger(__name__)

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


def _is_heading_para(paragraph) -> bool:
    sid = getattr(paragraph.style, "style_id", "") or ""
    if sid in _HEADING_STYLE_IDS:
        return True
    sname = (getattr(paragraph.style, "name", "") or "").lower()
    if "heading" in sname or "\u0437\u0430\u0433\u043e\u043b\u043e\u0432" in sname:
        return True
    for pPr in walk_style_pPr(paragraph):
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
    for pPr in walk_style_pPr(paragraph):
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


@dataclass(slots=True)
class AutoFixResult:
    output_file_path: str | None
    details: list[str]


def apply_safe_autofixes(
    file_path: str, rules: dict | None, findings: list[Finding],
    admin_autofix_config: dict | None = None,
) -> AutoFixResult:
    source = Path(file_path)
    if source.suffix.lower() != ".docx" or not source.exists():
        return AutoFixResult(output_file_path=None, details=[])

    admin_cfg = admin_autofix_config or {}
    cfg = _AutoFixConfig.from_rules(rules, admin_defaults=admin_cfg.get("defaults"))
    if not cfg.enabled:
        return AutoFixResult(output_file_path=None, details=[])

    safety = admin_cfg.get("safety_limits", {})
    max_changes = int(safety.get("max_changes_per_document", 500))
    skip_toc = bool(safety.get("skip_toc", True))
    skip_headings_safety = bool(safety.get("skip_headings", True))
    skip_tables_safety = bool(safety.get("skip_tables", True))
    skip_margins_safety = bool(safety.get("skip_margin_normalization", True))

    try:
        doc = Document(str(source))
    except Exception:
        logger.warning("Autofix: cannot open DOCX %s", file_path)
        return AutoFixResult(output_file_path=None, details=[])

    toc_indices: set[int] = set()
    if skip_toc:
        toc_indices = detect_toc_paragraph_indices(doc)

    changed = False
    details: list[str] = []
    change_count = 0

    if cfg.normalize_font_color:
        if fix_font_color_styles(doc, details):
            changed = True

    if cfg.remove_italic:
        if fix_italic_styles(doc, details):
            changed = True

    if cfg.normalize_list_markers:
        if fix_numbering_bullets(doc, cfg.font_name, details):
            changed = True

    if cfg.normalize_margins and not skip_margins_safety:
        if preflight_margins_safe(doc, cfg.margins_mm):
            for sec_idx, section in enumerate(doc.sections):
                if fix_section_margins(section, cfg.margins_mm, sec_idx, details):
                    changed = True
                    change_count += 1
        else:
            logger.info("Autofix: margin normalization skipped — tables would overflow")

    body_start = 0
    for i, p in enumerate(doc.paragraphs):
        if _is_heading_para(p):
            body_start = i
            break

    for idx, paragraph in enumerate(doc.paragraphs):
        if change_count >= max_changes:
            break

        text = (paragraph.text or "").strip()
        if not text:
            continue

        if cfg.normalize_font_color:
            if fix_font_color_runs(paragraph, idx, details):
                changed = True
                change_count += 1

        if cfg.remove_italic:
            if fix_remove_italic(paragraph, idx, details):
                changed = True
                change_count += 1

        if cfg.remove_caption_trailing_dot:
            if fix_caption_trailing_dot(paragraph, idx, details):
                changed = True
                change_count += 1

        if idx in toc_indices:
            continue

        if _is_heading_para(paragraph):
            if not skip_headings_safety and cfg.normalize_headings:
                if _fix_heading(paragraph, idx, cfg, details):
                    changed = True
                    change_count += 1
            continue

        if _should_skip_para(paragraph):
            continue

        if idx < body_start:
            continue

        eff_align = effective_alignment(paragraph)
        if eff_align in (WD_PARAGRAPH_ALIGNMENT.CENTER, WD_PARAGRAPH_ALIGNMENT.RIGHT):
            continue

        is_list = _is_list_para(paragraph) or is_manual_list_para(text)
        pf = paragraph.paragraph_format

        if is_list and cfg.normalize_list_markers:
            if fix_markers_text(paragraph, idx, details):
                changed = True
                change_count += 1

        if is_list and cfg.normalize_list_indent:
            if fix_list_indent(paragraph, idx, details):
                changed = True
                change_count += 1

        if not is_list and cfg.normalize_dashes:
            if fix_dashes_in_text(paragraph, idx, details):
                changed = True
                change_count += 1

        if not is_list and cfg.normalize_alignment:
            if eff_align != WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
                changed = True
                change_count += 1
                details.append(f"Paragraph #{idx + 1}: alignment justify")

        if cfg.normalize_line_spacing:
            eff_ls = effective_line_spacing(paragraph)
            if eff_ls is not None and abs(eff_ls - cfg.line_spacing) > 0.05:
                pf.line_spacing = cfg.line_spacing
                changed = True
                change_count += 1
                details.append(f"Paragraph #{idx + 1}: line spacing {cfg.line_spacing}")

        if not is_list and cfg.normalize_first_line_indent:
            eff_indent = effective_first_line_indent_mm(paragraph)
            if abs(eff_indent - cfg.first_line_indent_mm) > 0.5:
                pf.first_line_indent = Mm(cfg.first_line_indent_mm)
                changed = True
                change_count += 1
                details.append(f"Paragraph #{idx + 1}: first line indent {cfg.first_line_indent_mm} mm")

        if not is_list and cfg.normalize_spacing_before_after:
            eff_sb = effective_space_before_pt(paragraph)
            if abs(eff_sb - cfg.space_before_pt) > 0.2:
                pf.space_before = Pt(cfg.space_before_pt)
                changed = True
                change_count += 1
                details.append(f"Paragraph #{idx + 1}: spacing before {cfg.space_before_pt} pt")
            eff_sa = effective_space_after_pt(paragraph)
            if abs(eff_sa - cfg.space_after_pt) > 0.2:
                pf.space_after = Pt(cfg.space_after_pt)
                changed = True
                change_count += 1
                details.append(f"Paragraph #{idx + 1}: spacing after {cfg.space_after_pt} pt")

        if cfg.normalize_font:
            font_changed = False
            for run in paragraph.runs:
                if is_field_code_run(run):
                    continue
                eff_name = effective_font_name(run, paragraph)
                if cfg.font_name and eff_name and eff_name != cfg.font_name:
                    run.font.name = cfg.font_name
                    font_changed = True
                eff_size = effective_font_size_pt(run, paragraph)
                if eff_size is not None and abs(eff_size - cfg.font_size_pt) > 0.2:
                    run.font.size = Pt(cfg.font_size_pt)
                    font_changed = True
            if font_changed:
                changed = True
                change_count += 1
                details.append(f"Paragraph #{idx + 1}: font {cfg.font_name}, {cfg.font_size_pt}pt")

    if cfg.normalize_table_width and not skip_tables_safety and clamp_overflow_table_widths(doc, details):
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
        postprocess_fixed_docx(source, output)
    except Exception:
        logger.warning("Autofix: postprocessing failed for %s, using python-docx output", output)

    findings.append(
        Finding(
            title="\u0410\u0432\u0442\u043e\u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f",
            category="autofix",
            severity="advice",
            expected="",
            found="",
            location="\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442",
            recommendation="\u0421\u043a\u0430\u0447\u0430\u0439\u0442\u0435 \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043d\u044b\u0439 DOCX",
            auto_fixed=True,
            auto_fix_details="; ".join(details[:30]),
        )
    )

    return AutoFixResult(output_file_path=str(output), details=details)


def _fix_heading(paragraph, idx: int, cfg: "_AutoFixConfig", details: list[str]) -> bool:
    changed = False
    for run in paragraph.runs:
        if is_field_code_run(run):
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
    normalize_font_color: bool
    target_font_color: str
    remove_italic: bool
    normalize_list_indent: bool
    normalize_list_markers: bool
    normalize_dashes: bool
    remove_caption_trailing_dot: bool
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
    def from_rules(cls, rules: dict | None, admin_defaults: dict | None = None) -> "_AutoFixConfig":
        ad = admin_defaults or {}
        blocks = {
            str(b.get("key")): b
            for b in (rules or {}).get("blocks", [])
            if isinstance(b, dict)
        }
        auto = blocks.get("autofix", {})
        params = auto.get("params") or {}
        enabled = bool(auto.get("enabled", ad.get("enabled", True)))

        typography = blocks.get("typography", {})
        body = (typography.get("params") or {}).get("body") or {}

        layout = blocks.get("layout", {})
        layout_params = layout.get("params") or {}

        heading = blocks.get("heading_formatting", {})
        heading_params = heading.get("params") or {}

        return cls(
            enabled=enabled,
            normalize_alignment=bool(params.get("normalize_alignment", ad.get("normalize_alignment", True))),
            normalize_line_spacing=bool(params.get("normalize_line_spacing", ad.get("normalize_line_spacing", True))),
            normalize_first_line_indent=bool(params.get("normalize_first_line_indent", ad.get("normalize_first_line_indent", True))),
            normalize_spacing_before_after=bool(params.get("normalize_spacing_before_after", ad.get("normalize_spacing_before_after", True))),
            normalize_font=bool(params.get("normalize_font", ad.get("normalize_font", True))),
            normalize_margins=bool(params.get("normalize_margins", ad.get("normalize_margins", False))),
            normalize_headings=bool(params.get("normalize_headings", ad.get("normalize_headings", True))),
            normalize_table_width=bool(params.get("normalize_table_width", ad.get("normalize_table_width", True))),
            normalize_font_color=bool(params.get("normalize_font_color", ad.get("normalize_font_color", True))),
            target_font_color=str(params.get("target_font_color", ad.get("target_font_color", "000000"))),
            remove_italic=bool(params.get("remove_italic", ad.get("remove_italic", True))),
            normalize_list_indent=bool(params.get("normalize_list_indent", ad.get("normalize_list_indent", True))),
            normalize_list_markers=bool(params.get("normalize_list_markers", ad.get("normalize_list_markers", True))),
            normalize_dashes=bool(params.get("normalize_dashes", ad.get("normalize_dashes", True))),
            remove_caption_trailing_dot=bool(params.get("remove_caption_trailing_dot", ad.get("remove_caption_trailing_dot", True))),
            line_spacing=float(body.get("line_spacing", 1.5)),
            first_line_indent_mm=float(body.get("first_line_indent_mm", 12.5)),
            space_before_pt=float(params.get("space_before_pt", ad.get("space_before_pt", 0))),
            space_after_pt=float(params.get("space_after_pt", ad.get("space_after_pt", 0))),
            font_name=str(body.get("font", "Times New Roman")),
            font_size_pt=float(body.get("size_pt", 14)),
            margins_mm=layout_params.get(
                "margins_mm", {"left": 30, "right": 15, "top": 20, "bottom": 25},
            ),
            heading_font=str(heading_params.get("font", body.get("font", "Times New Roman"))),
            heading_size_pt=float(heading_params.get("size_pt", body.get("size_pt", 14))),
            heading_bold=bool(heading_params.get("require_bold", True)),
        )
