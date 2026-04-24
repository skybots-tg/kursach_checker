from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

from app.rules_engine.autofix_config import AutoFixConfig as _AutoFixConfig
from app.rules_engine.autofix_refresh import refresh_fields_via_libreoffice
from app.rules_engine.autofix_headings import (
    ensure_blank_before_subheadings,
    enforce_chapter_page_breaks,
    enforce_heading_bold,
    enforce_subheading_alignment,
    fix_heading as _fix_heading,
    fix_remove_underline,
    promote_to_heading as _promote_to_heading,
)
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
    fix_page_break_before,
    fix_remove_highlight,
    fix_remove_italic,
    fix_remove_strange_chars,
    fix_strip_markdown_artifacts,
    fix_section_margins,
    fix_table_cell_spacing,
    is_field_code_run,
    is_manual_list_para,
    iter_table_cell_paragraphs,
    postprocess_fixed_docx,
    preflight_margins_safe,
    remove_empty_paras_before_page_breaks,
    remove_manual_page_breaks,
)
from app.rules_engine.autofix_bibliography import (
    enforce_bibliography_entry_formatting,
    fix_bibliography_order_and_numbering,
)
from app.rules_engine.autofix_captions import fix_caption_positions
from app.rules_engine.autofix_lists import convert_informal_lists
from app.rules_engine.autofix_toc import insert_toc_field, detect_manual_toc_entry_indices
from app.rules_engine.autofix_split_breaks import split_soft_break_paragraphs
from app.rules_engine.autofix_redundant_breaks import remove_redundant_manual_page_breaks
from app.rules_engine.autofix_toc_normalize import normalize_toc_heading_formatting
from app.rules_engine.autofix_whitespace import (
    collapse_excessive_empty_paras,
    fix_normalize_left_indent,
    fix_strip_leading_whitespace,
    normalize_doc_defaults_spacing,
)
from app.rules_engine.checks_content import ALLOWED_CHARS_RE as _ALLOWED_CHARS_RE
from app.rules_engine.heading_detection import (
    CHAPTER_RE as _CHAPTER_RE,
    TOC_LINE_TAIL_RE as _TOC_LINE_TAIL_RE,
    detect_heading_candidate,
    detect_heading_via_toc,
    normalize_toc_entry,
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

def _collect_toc_heading_levels(doc, toc_indices: set[int]) -> dict[str, int]:
    """Gather normalized TOC-entry titles → heading level for promotion.

    Used as a *fallback* heading detector: when a body paragraph does not
    match the normal «Глава N» / «1.2.» regexes but the document's table
    of contents explicitly lists it as a section title, we still promote
    it to a Word heading. This makes the autofix robust against loose
    wordings students use — e.g. "I Организационно-технологический
    раздел" or all-caps titles that skip the «Глава» keyword.

    Returns a dict mapping ``normalize_toc_entry(text)`` → ``level`` so
    the caller can decide how deeply to nest the heading. Level is
    inferred from the entry prefix: ``1.2`` → 2, ``1.2.3`` → 3, otherwise
    level 1.
    """
    result: dict[str, int] = {}
    paragraphs = doc.paragraphs
    for idx in toc_indices:
        if idx < 0 or idx >= len(paragraphs):
            continue
        raw = (paragraphs[idx].text or "").strip()
        if not raw or len(raw) > 250:
            continue
        key = normalize_toc_entry(raw)
        if not key:
            continue
        # Skip generic TOC headers themselves.
        if key in ("содержание", "оглавление"):
            continue
        level = _infer_toc_entry_level(key)
        result[key] = level
    return result


def _infer_toc_entry_level(normalized: str) -> int:
    import re as _re
    m = _re.match(r"^(\d+(?:\.\d+)*)", normalized)
    if m:
        parts = m.group(1).split(".")
        return max(1, min(len(parts), 3))
    return 1


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
    max_paragraphs = int(safety.get("max_paragraphs_touched", 2000))
    skip_toc = bool(safety.get("skip_toc", True))
    skip_headings_safety = bool(safety.get("skip_headings", True))
    allow_promote = bool(safety.get("allow_promote_heading_candidates", cfg.promote_heading_candidates))
    skip_tables_safety = bool(safety.get("skip_tables", True))
    skip_margins_safety = bool(safety.get("skip_margin_normalization", True))
    use_libreoffice_refresh = bool(safety.get("libreoffice_toc_refresh", False))

    try:
        doc = Document(str(source))
    except Exception:
        logger.warning("Autofix: cannot open DOCX %s", file_path)
        return AutoFixResult(output_file_path=None, details=[])

    changed = False
    details: list[str] = []
    change_count = 0

    # Convert soft line breaks into proper paragraph marks BEFORE we compute
    # any indices (the splitting renumbers paragraphs). Students often press
    # Shift+Enter between sentences, which prevents the body-text indent and
    # paragraph-style passes from working correctly because the entire
    # introduction lives in a single ``<w:p>``.
    if split_soft_break_paragraphs(doc, details):
        changed = True

    toc_indices: set[int] = set()
    if skip_toc:
        toc_indices = detect_toc_paragraph_indices(doc)

    # Manual TOC lines usually don't carry a page-number tail (students just
    # type the section titles). ``detect_toc_paragraph_indices`` only catches
    # entries that do, so we augment ``toc_indices`` with a more permissive
    # heuristic pass before running any heading/normalization logic. This is
    # essential: without it, the subsequent TOC-based heading promotion would
    # mark the manual TOC lines themselves as headings and ``_remove_manual_
    # toc_entries`` would then refuse to delete them, leaving two tables of
    # contents glued together in the output.
    toc_indices |= detect_manual_toc_entry_indices(doc)

    toc_heading_levels: dict[str, int] = _collect_toc_heading_levels(doc, toc_indices)


    if cfg.normalize_line_spacing or cfg.normalize_spacing_before_after:
        if normalize_doc_defaults_spacing(
            doc, cfg.line_spacing, cfg.space_after_pt, details,
        ):
            changed = True

    if cfg.normalize_font_color:
        if fix_font_color_styles(doc, details):
            changed = True

    if cfg.remove_italic:
        if fix_italic_styles(doc, details):
            changed = True

    if cfg.normalize_list_markers:
        if fix_numbering_bullets(doc, cfg.font_name, details, cfg.list_marker_char):
            changed = True

    if cfg.convert_informal_lists:
        if convert_informal_lists(
            doc, cfg.informal_list_markers, cfg.list_marker_char,
            cfg.informal_list_min_consecutive, toc_indices, details,
        ):
            changed = True

    if cfg.normalize_margins and not skip_margins_safety:
        if preflight_margins_safe(doc, cfg.margins_mm):
            for sec_idx, section in enumerate(doc.sections):
                if fix_section_margins(section, cfg.margins_mm, sec_idx, details):
                    changed = True
                    change_count += 1
        else:
            logger.info("Autofix: margin normalization skipped — tables would overflow")

    for idx, paragraph in enumerate(doc.paragraphs):
        text = (paragraph.text or "").strip()
        if not text:
            continue
        para_label = f"\u0410\u0431\u0437\u0430\u0446 #{idx + 1}"
        if cfg.remove_highlight:
            if fix_remove_highlight(paragraph, para_label, details):
                changed = True
        if cfg.remove_strange_chars:
            if fix_remove_strange_chars(paragraph, para_label, details, _ALLOWED_CHARS_RE):
                changed = True
        if cfg.strip_leading_whitespace and idx not in toc_indices:
            if fix_strip_leading_whitespace(paragraph, para_label, details):
                changed = True
        if (
            cfg.fix_section_breaks
            and idx > 0
            and len(text) <= 100
            and idx not in toc_indices
        ):
            if not _TOC_LINE_TAIL_RE.search(text):
                needs_break = any(s in text.lower() for s in cfg.section_break_sections)
                if not needs_break:
                    needs_break = bool(_CHAPTER_RE.match(text))
                if needs_break:
                    prev_idx = idx - 1
                    while prev_idx >= 0:
                        prev_para = doc.paragraphs[prev_idx]
                        if (prev_para.text or "").strip():
                            break
                        if remove_manual_page_breaks(prev_para):
                            changed = True
                        prev_idx -= 1
                    if remove_manual_page_breaks(paragraph):
                        changed = True
                    if fix_page_break_before(paragraph, para_label, details):
                        changed = True

    body_start = 0
    for i, p in enumerate(doc.paragraphs):
        if _is_heading_para(p):
            body_start = i
            break

    para_count = 0
    for idx, paragraph in enumerate(doc.paragraphs):
        if para_count >= max_paragraphs:
            break

        text = (paragraph.text or "").strip()
        if not text:
            continue

        para_label = f"\u0410\u0431\u0437\u0430\u0446 #{idx + 1}"
        para_touched = False

        if cfg.normalize_font_color:
            if fix_font_color_runs(paragraph, para_label, details):
                changed = True
                para_touched = True

        if cfg.remove_italic:
            if fix_remove_italic(paragraph, para_label, details):
                changed = True
                para_touched = True

        if cfg.remove_underline:
            if fix_remove_underline(paragraph, para_label, details):
                changed = True
                para_touched = True

        if cfg.remove_caption_trailing_dot:
            if fix_caption_trailing_dot(paragraph, para_label, details):
                changed = True
                para_touched = True

        if idx in toc_indices:
            if para_touched:
                para_count += 1
            continue

        is_heading = _is_heading_para(paragraph)
        candidate_level = detect_heading_candidate(text) if not is_heading else None
        if not is_heading and candidate_level is None and toc_heading_levels:
            candidate_level = detect_heading_via_toc(text, toc_heading_levels)

        if is_heading:
            if not skip_headings_safety and cfg.normalize_headings:
                if _fix_heading(paragraph, idx, cfg, details):
                    changed = True
                    para_touched = True
            if para_touched:
                para_count += 1
            continue

        if candidate_level is not None and allow_promote:
            # «Содержание»/«Оглавление» must stay as a plain centered paragraph
            # (client's explicit request). Skip heading promotion for it —
            # normalize_toc_heading_formatting will format it correctly later.
            low = text.strip().lower().rstrip(":.")
            if low in ("содержание", "оглавление"):
                if para_touched:
                    para_count += 1
                continue
            if _promote_to_heading(paragraph, candidate_level, idx, cfg, details):
                changed = True
                para_touched = True
            if para_touched:
                para_count += 1
            continue

        if candidate_level is not None:
            if para_touched:
                para_count += 1
            continue

        if _should_skip_para(paragraph):
            if para_touched:
                para_count += 1
            continue

        if idx < body_start:
            if para_touched:
                para_count += 1
            continue

        eff_align = effective_alignment(paragraph)
        is_center_like = eff_align in (
            WD_PARAGRAPH_ALIGNMENT.CENTER,
            WD_PARAGRAPH_ALIGNMENT.RIGHT,
        )

        is_word_list = _is_list_para(paragraph)
        is_manual = not is_word_list and is_manual_list_para(text)
        is_list = is_word_list or is_manual
        pf = paragraph.paragraph_format

        if not is_center_like and is_list and cfg.normalize_list_markers:
            if fix_markers_text(paragraph, para_label, details, cfg.list_marker_char):
                changed = True
                para_touched = True

        if not is_center_like and is_word_list and cfg.normalize_list_indent:
            if fix_list_indent(paragraph, para_label, details):
                changed = True
                para_touched = True

        if cfg.normalize_dashes:
            if fix_dashes_in_text(paragraph, para_label, details):
                changed = True
                para_touched = True

        if fix_strip_markdown_artifacts(paragraph, para_label, details):
            changed = True
            para_touched = True

        if not is_center_like and cfg.normalize_alignment:
            if eff_align != WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
                changed = True
                para_touched = True
                details.append(f"{para_label}: выравнивание по ширине")

        if cfg.normalize_line_spacing:
            eff_ls = effective_line_spacing(paragraph)
            if eff_ls is not None and abs(eff_ls - cfg.line_spacing) > 0.05:
                pf.line_spacing = cfg.line_spacing
                changed = True
                para_touched = True
                details.append(f"{para_label}: межстрочный интервал {cfg.line_spacing}")

        if not is_center_like and not is_word_list and cfg.normalize_first_line_indent:
            eff_indent = effective_first_line_indent_mm(paragraph)
            if abs(eff_indent - cfg.first_line_indent_mm) > 0.5:
                pf.first_line_indent = Mm(cfg.first_line_indent_mm)
                changed = True
                para_touched = True
                details.append(f"{para_label}: абзацный отступ {cfg.first_line_indent_mm} мм")

        if not is_center_like and not is_list and cfg.normalize_body_left_indent:
            if fix_normalize_left_indent(paragraph, para_label, details):
                changed = True
                para_touched = True

        if not is_center_like and cfg.normalize_spacing_before_after:
            eff_sb = effective_space_before_pt(paragraph)
            if abs(eff_sb - cfg.space_before_pt) > 0.2:
                pf.space_before = Pt(cfg.space_before_pt)
                changed = True
                para_touched = True
                details.append(f"{para_label}: интервал до {cfg.space_before_pt} пт")
            eff_sa = effective_space_after_pt(paragraph)
            if abs(eff_sa - cfg.space_after_pt) > 0.2:
                pf.space_after = Pt(cfg.space_after_pt)
                changed = True
                para_touched = True
                details.append(f"{para_label}: интервал после {cfg.space_after_pt} пт")

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
                para_touched = True
                details.append(f"{para_label}: шрифт {cfg.font_name}, {cfg.font_size_pt} пт")

        if para_touched:
            para_count += 1

    for t_idx, t_para in enumerate(iter_table_cell_paragraphs(doc)):
        if para_count >= max_paragraphs:
            break
        t_text = (t_para.text or "").strip()
        t_label = f"Абзац таблицы #{t_idx + 1}"
        t_touched = False
        if cfg.normalize_line_spacing:
            if fix_table_cell_spacing(
                t_para, cfg.table_line_spacing, t_label, details,
            ):
                changed = True
                t_touched = True
        if not t_text:
            if t_touched:
                para_count += 1
            continue
        if cfg.normalize_font_color:
            if fix_font_color_runs(t_para, t_label, details):
                changed = True
                t_touched = True
        if cfg.remove_italic:
            if fix_remove_italic(t_para, t_label, details):
                changed = True
                t_touched = True
        if cfg.remove_caption_trailing_dot:
            if fix_caption_trailing_dot(t_para, t_label, details):
                changed = True
                t_touched = True
        t_is_list = _is_list_para(t_para) or is_manual_list_para(t_text)
        if t_is_list and cfg.normalize_list_markers:
            if fix_markers_text(t_para, t_label, details, cfg.list_marker_char):
                changed = True
                t_touched = True
        if t_is_list and cfg.normalize_list_indent:
            if fix_list_indent(t_para, t_label, details):
                changed = True
                t_touched = True
        if cfg.normalize_dashes:
            if fix_dashes_in_text(t_para, t_label, details):
                changed = True
                t_touched = True
        if fix_strip_markdown_artifacts(t_para, t_label, details):
            changed = True
            t_touched = True
        if t_touched:
            para_count += 1

    if cfg.normalize_table_width and not skip_tables_safety and clamp_overflow_table_widths(doc, details):
        changed = True

    if cfg.generate_toc:
        if insert_toc_field(doc, toc_indices, details):
            changed = True

    if cfg.normalize_toc_heading:
        if normalize_toc_heading_formatting(doc, details, cfg=cfg):
            changed = True

    if cfg.fix_bibliography:
        if fix_bibliography_order_and_numbering(doc, details):
            changed = True
        if enforce_bibliography_entry_formatting(
            doc,
            details,
            line_spacing=cfg.line_spacing,
            first_line_indent_mm=cfg.first_line_indent_mm,
            space_after_pt=cfg.space_after_pt,
            font_name=cfg.font_name,
            font_size_pt=cfg.font_size_pt,
        ):
            changed = True

    if getattr(cfg, "fix_caption_positions", True):
        if fix_caption_positions(doc, details):
            changed = True

    if enforce_subheading_alignment(doc, cfg, details):
        changed = True

    if enforce_heading_bold(doc, cfg, details):
        changed = True

    if cfg.fix_section_breaks:
        if enforce_chapter_page_breaks(doc, details):
            changed = True

    if cfg.ensure_subheading_spacing:
        if ensure_blank_before_subheadings(doc, details):
            changed = True

    if cfg.collapse_empty_paras:
        if collapse_excessive_empty_paras(doc, cfg.max_consecutive_empty_paras, details):
            changed = True

    if changed:
        if remove_redundant_manual_page_breaks(doc, details):
            pass
        if remove_empty_paras_before_page_breaks(doc, details):
            pass

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

    if cfg.generate_toc and use_libreoffice_refresh:
        if refresh_fields_via_libreoffice(output, details):
            logger.info("Autofix: LibreOffice refreshed fields for %s", output)

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


