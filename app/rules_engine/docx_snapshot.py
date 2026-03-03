from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docx import Document


@dataclass(slots=True)
class SectionMargins:
    left_mm: float | None
    right_mm: float | None
    top_mm: float | None
    bottom_mm: float | None


@dataclass(slots=True)
class ParagraphSnapshot:
    index: int
    text: str
    style_name: str
    alignment: str | None
    first_line_indent_mm: float | None
    line_spacing: float | None
    has_explicit_before: bool
    has_explicit_after: bool
    runs_fonts: list[str]
    runs_size_pt: list[float]

    @property
    def is_heading(self) -> bool:
        lower = self.style_name.lower()
        return "heading" in lower or "заголов" in lower


@dataclass(slots=True)
class DocumentSnapshot:
    path: Path
    extension: str
    size: int
    sections: list[SectionMargins]
    paragraphs: list[ParagraphSnapshot]
    heading_titles: list[str]
    full_text: str
    comments_count: int
    revisions_present: bool


def _mm_from_emu(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / 36000, 2)


def _safe_doc_attr_length(obj: object, attr_name: str) -> int:
    value = getattr(obj, attr_name, None)
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 0


def _normalize_alignment(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _extract_run_fonts(paragraph) -> list[str]:
    values: list[str] = []
    for run in paragraph.runs:
        if run.font and run.font.name:
            values.append(run.font.name.strip())
    return values


def _extract_run_sizes(paragraph) -> list[float]:
    values: list[float] = []
    for run in paragraph.runs:
        if run.font and run.font.size:
            values.append(round(float(run.font.size.pt), 2))
    return values


def _section_margins(doc: Document) -> list[SectionMargins]:
    result: list[SectionMargins] = []
    for section in doc.sections:
        result.append(
            SectionMargins(
                left_mm=_mm_from_emu(section.left_margin),
                right_mm=_mm_from_emu(section.right_margin),
                top_mm=_mm_from_emu(section.top_margin),
                bottom_mm=_mm_from_emu(section.bottom_margin),
            )
        )
    return result


def _paragraphs(doc: Document) -> list[ParagraphSnapshot]:
    result: list[ParagraphSnapshot] = []
    for idx, paragraph in enumerate(doc.paragraphs):
        text = (paragraph.text or "").strip()
        pformat = paragraph.paragraph_format
        indent = _mm_from_emu(getattr(pformat.first_line_indent, "emu", None))
        line_spacing = None
        if pformat.line_spacing and isinstance(pformat.line_spacing, float):
            line_spacing = float(pformat.line_spacing)

        result.append(
            ParagraphSnapshot(
                index=idx,
                text=text,
                style_name=getattr(paragraph.style, "name", "") or "",
                alignment=_normalize_alignment(paragraph.alignment),
                first_line_indent_mm=indent,
                line_spacing=line_spacing,
                has_explicit_before=pformat.space_before is not None,
                has_explicit_after=pformat.space_after is not None,
                runs_fonts=_extract_run_fonts(paragraph),
                runs_size_pt=_extract_run_sizes(paragraph),
            )
        )
    return result


def _extract_headings(paragraphs: list[ParagraphSnapshot]) -> list[str]:
    return [p.text.lower() for p in paragraphs if p.text and p.is_heading]


def _guess_revisions(doc: Document) -> bool:
    xml = doc._element.xml  # noqa: SLF001
    return bool(re.search(r"w:(ins|del|moveFrom|moveTo)\\b", xml))


def build_snapshot(file_path: str) -> DocumentSnapshot:
    path = Path(file_path)
    extension = path.suffix.lower()
    size = path.stat().st_size if path.exists() else 0

    if extension != ".docx":
        return DocumentSnapshot(
            path=path,
            extension=extension,
            size=size,
            sections=[],
            paragraphs=[],
            heading_titles=[],
            full_text="",
            comments_count=0,
            revisions_present=False,
        )

    doc = Document(str(path))
    paragraphs = _paragraphs(doc)

    return DocumentSnapshot(
        path=path,
        extension=extension,
        size=size,
        sections=_section_margins(doc),
        paragraphs=paragraphs,
        heading_titles=_extract_headings(paragraphs),
        full_text="\n".join(p.text for p in paragraphs if p.text),
        comments_count=_safe_doc_attr_length(doc, "comments"),
        revisions_present=_guess_revisions(doc),
    )

