"""Autofix configuration dataclass — parsed from rules JSON and admin defaults."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AutoFixConfig:
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
    list_marker_char: str
    normalize_dashes: bool
    remove_caption_trailing_dot: bool
    remove_highlight: bool
    remove_strange_chars: bool
    fix_section_breaks: bool
    promote_heading_candidates: bool
    section_break_sections: list[str]
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
    def from_rules(cls, rules: dict | None, admin_defaults: dict | None = None) -> "AutoFixConfig":
        ad = admin_defaults or {}
        blocks = {
            str(b.get("key")): b
            for b in (rules or {}).get("blocks", [])
            if isinstance(b, dict)
        }
        auto = blocks.get("autofix", {})
        p = auto.get("params") or {}

        def _b(k: str, d: bool = True) -> bool:
            return bool(p.get(k, ad.get(k, d)))

        body = ((blocks.get("typography", {}).get("params") or {}).get("body") or {})
        lp = (blocks.get("layout", {}).get("params") or {})
        hp = (blocks.get("heading_formatting", {}).get("params") or {})
        sb = (blocks.get("section_breaks", {}).get("params") or {})
        _dflt_sec = [
            "содержание", "оглавление", "введение", "заключение",
            "список литературы", "список использованных источников",
        ]

        return cls(
            enabled=bool(auto.get("enabled", ad.get("enabled", True))),
            normalize_alignment=_b("normalize_alignment"),
            normalize_line_spacing=_b("normalize_line_spacing"),
            normalize_first_line_indent=_b("normalize_first_line_indent"),
            normalize_spacing_before_after=_b("normalize_spacing_before_after"),
            normalize_font=_b("normalize_font"),
            normalize_margins=_b("normalize_margins", False),
            normalize_headings=_b("normalize_headings"),
            normalize_table_width=_b("normalize_table_width"),
            normalize_font_color=_b("normalize_font_color"),
            target_font_color=str(p.get("target_font_color", ad.get("target_font_color", "000000"))),
            remove_italic=_b("remove_italic"),
            normalize_list_indent=_b("normalize_list_indent"),
            normalize_list_markers=_b("normalize_list_markers"),
            list_marker_char=str(p.get("list_marker_char", ad.get("list_marker_char", "-"))),
            normalize_dashes=_b("normalize_dashes"),
            remove_caption_trailing_dot=_b("remove_caption_trailing_dot"),
            remove_highlight=_b("remove_highlight"),
            remove_strange_chars=_b("remove_strange_chars"),
            fix_section_breaks=_b("fix_section_breaks"),
            promote_heading_candidates=_b("promote_heading_candidates"),
            section_break_sections=[s.lower() for s in sb.get("sections_requiring_break", _dflt_sec)],
            line_spacing=float(body.get("line_spacing", 1.5)),
            first_line_indent_mm=float(body.get("first_line_indent_mm", 12.5)),
            space_before_pt=float(p.get("space_before_pt", ad.get("space_before_pt", 0))),
            space_after_pt=float(p.get("space_after_pt", ad.get("space_after_pt", 0))),
            font_name=str(body.get("font", "Times New Roman")),
            font_size_pt=float(body.get("size_pt", 14)),
            margins_mm=lp.get("margins_mm", {"left": 30, "right": 15, "top": 20, "bottom": 25}),
            heading_font=str(hp.get("font", body.get("font", "Times New Roman"))),
            heading_size_pt=float(hp.get("size_pt", body.get("size_pt", 14))),
            heading_bold=bool(hp.get("require_bold", True)),
        )
