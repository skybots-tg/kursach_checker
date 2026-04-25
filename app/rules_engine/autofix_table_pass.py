"""Table cell autofix pass.

Processes paragraphs inside table cells: normalizes line spacing, font
colour, italic, captions, list markers, dashes, and markdown artifacts.
"""
from __future__ import annotations

from app.rules_engine.autofix_helpers import (
    fix_caption_trailing_dot,
    fix_dashes_in_text,
    fix_font_color_runs,
    fix_list_indent,
    fix_markers_text,
    fix_remove_italic,
    fix_strip_markdown_artifacts,
    fix_table_cell_spacing,
    is_manual_list_para,
    iter_table_cell_paragraphs,
)
from app.rules_engine.autofix_para_classify import is_list_para


def process_table_cells(
    doc,
    cfg,
    max_paragraphs: int,
    para_count: int,
    details: list[str],
) -> tuple[bool, int]:
    """Apply fixes to every paragraph inside table cells.

    Returns ``(changed, new_para_count)`` so the caller can accumulate
    the touched-paragraph counter.
    """
    changed = False
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
        t_is_list = is_list_para(t_para) or is_manual_list_para(t_text)
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
    return changed, para_count
