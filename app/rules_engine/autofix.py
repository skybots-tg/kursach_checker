from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Mm, Pt

from app.rules_engine.findings import Finding


@dataclass(slots=True)
class AutoFixResult:
    output_file_path: str | None
    details: list[str]


def apply_safe_autofixes(file_path: str, rules: dict | None, findings: list[Finding]) -> AutoFixResult:
    source = Path(file_path)
    if source.suffix.lower() != ".docx" or not source.exists():
        return AutoFixResult(output_file_path=None, details=[])

    cfg = _AutoFixConfig.from_rules(rules)
    if not cfg.enabled:
        return AutoFixResult(output_file_path=None, details=[])

    doc = Document(str(source))
    changed = False
    details: list[str] = []

    for idx, paragraph in enumerate(doc.paragraphs):
        text = (paragraph.text or "").strip()
        style_name = getattr(paragraph.style, "name", "") or ""
        if not text:
            continue
        if _is_heading(style_name):
            continue

        pf = paragraph.paragraph_format

        if cfg.normalize_alignment and paragraph.alignment != WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            changed = True
            details.append(f"Абзац #{idx + 1}: выравнивание по ширине")

        if cfg.normalize_line_spacing:
            curr = pf.line_spacing
            curr_float = float(curr) if isinstance(curr, float) else None
            if curr_float is None or abs(curr_float - cfg.line_spacing) > 0.05:
                pf.line_spacing = cfg.line_spacing
                changed = True
                details.append(f"Абзац #{idx + 1}: межстрочный интервал {cfg.line_spacing}")

        if cfg.normalize_first_line_indent:
            curr_mm = None
            if pf.first_line_indent is not None:
                curr_mm = round(float(pf.first_line_indent.mm), 2)
            if curr_mm is None or abs(curr_mm - cfg.first_line_indent_mm) > 0.5:
                pf.first_line_indent = Mm(cfg.first_line_indent_mm)
                changed = True
                details.append(f"Абзац #{idx + 1}: красная строка {cfg.first_line_indent_mm} мм")

        if cfg.normalize_spacing_before_after:
            if pf.space_before is None or abs(float(pf.space_before.pt) - cfg.space_before_pt) > 0.2:
                pf.space_before = Pt(cfg.space_before_pt)
                changed = True
                details.append(f"Абзац #{idx + 1}: интервал до {cfg.space_before_pt} pt")
            if pf.space_after is None or abs(float(pf.space_after.pt) - cfg.space_after_pt) > 0.2:
                pf.space_after = Pt(cfg.space_after_pt)
                changed = True
                details.append(f"Абзац #{idx + 1}: интервал после {cfg.space_after_pt} pt")

        if cfg.normalize_font:
            for run in paragraph.runs:
                run_changed = False
                if cfg.font_name and run.font.name != cfg.font_name:
                    run.font.name = cfg.font_name
                    run_changed = True
                size_pt = float(run.font.size.pt) if run.font.size else None
                if size_pt is None or abs(size_pt - cfg.font_size_pt) > 0.2:
                    run.font.size = Pt(cfg.font_size_pt)
                    run_changed = True
                if run_changed:
                    changed = True
            if changed:
                details.append(f"Абзац #{idx + 1}: шрифт {cfg.font_name}, кегль {cfg.font_size_pt}")

    if not changed:
        return AutoFixResult(output_file_path=None, details=[])

    output = source.with_name(f"{source.stem}.fixed.docx")
    doc.save(str(output))

    if details:
        finding = findings[0] if findings else None
        _ = finding

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
            auto_fix_details="; ".join(details[:20]),
        )
    )

    return AutoFixResult(output_file_path=str(output), details=details)


@dataclass(slots=True)
class _AutoFixConfig:
    enabled: bool
    normalize_alignment: bool
    normalize_line_spacing: bool
    normalize_first_line_indent: bool
    normalize_spacing_before_after: bool
    normalize_font: bool
    line_spacing: float
    first_line_indent_mm: float
    space_before_pt: float
    space_after_pt: float
    font_name: str
    font_size_pt: float

    @classmethod
    def from_rules(cls, rules: dict | None) -> "_AutoFixConfig":
        blocks = {str(b.get("key")): b for b in (rules or {}).get("blocks", []) if isinstance(b, dict)}
        auto = blocks.get("autofix", {})
        params = auto.get("params") or {}
        enabled = bool(auto.get("enabled", True))

        typography = blocks.get("typography", {})
        body = (typography.get("params") or {}).get("body") or {}

        return cls(
            enabled=enabled,
            normalize_alignment=bool(params.get("normalize_alignment", True)),
            normalize_line_spacing=bool(params.get("normalize_line_spacing", True)),
            normalize_first_line_indent=bool(params.get("normalize_first_line_indent", True)),
            normalize_spacing_before_after=bool(params.get("normalize_spacing_before_after", True)),
            normalize_font=bool(params.get("normalize_font", True)),
            line_spacing=float(body.get("line_spacing", 1.5)),
            first_line_indent_mm=float(body.get("first_line_indent_mm", 12.5)),
            space_before_pt=float(params.get("space_before_pt", 0)),
            space_after_pt=float(params.get("space_after_pt", 0)),
            font_name=str(body.get("font", "Times New Roman")),
            font_size_pt=float(body.get("size_pt", 14)),
        )


def _is_heading(style_name: str) -> bool:
    lower = style_name.lower()
    return "heading" in lower or "заголов" in lower

