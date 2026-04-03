from __future__ import annotations

import re
import zipfile
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
    runs_bold: list[bool | None]

    @property
    def is_heading(self) -> bool:
        lower = self.style_name.lower()
        return "heading" in lower or "заголов" in lower

    @property
    def heading_level(self) -> int | None:
        if not self.is_heading:
            return None
        m = re.search(r"\d+", self.style_name)
        return int(m.group()) if m else 1


@dataclass(slots=True)
class HeadingSnapshot:
    index: int
    text: str
    level: int
    font_name: str | None
    font_size_pt: float | None
    bold: bool | None
    alignment: str | None


@dataclass(slots=True)
class CaptionSnapshot:
    index: int
    text: str
    caption_type: str
    number: int | None


@dataclass(slots=True)
class DocumentSnapshot:
    path: Path
    extension: str
    size: int
    sections: list[SectionMargins]
    paragraphs: list[ParagraphSnapshot]
    heading_titles: list[str]
    heading_snapshots: list[HeadingSnapshot]
    full_text: str
    comments_count: int
    revisions_present: bool
    has_page_numbers: bool
    has_toc: bool
    footnotes_count: int
    captions: list[CaptionSnapshot]
    is_encrypted: bool


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


def _extract_run_bolds(paragraph) -> list[bool | None]:
    return [run.bold for run in paragraph.runs]


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
                runs_bold=_extract_run_bolds(paragraph),
            )
        )
    return result


def _extract_headings(paragraphs: list[ParagraphSnapshot]) -> list[str]:
    return [p.text.lower() for p in paragraphs if p.text and p.is_heading]


def _extract_heading_snapshots(paragraphs: list[ParagraphSnapshot]) -> list[HeadingSnapshot]:
    result: list[HeadingSnapshot] = []
    for p in paragraphs:
        if not p.is_heading or not p.text:
            continue
        result.append(
            HeadingSnapshot(
                index=p.index,
                text=p.text,
                level=p.heading_level or 1,
                font_name=p.runs_fonts[0] if p.runs_fonts else None,
                font_size_pt=p.runs_size_pt[0] if p.runs_size_pt else None,
                bold=p.runs_bold[0] if p.runs_bold else None,
                alignment=p.alignment,
            )
        )
    return result


def _extract_captions(paragraphs: list[ParagraphSnapshot]) -> list[CaptionSnapshot]:
    result: list[CaptionSnapshot] = []
    for p in paragraphs:
        text = p.text.strip()
        if not text:
            continue
        m = re.match(r"^(?:Рисунок|Рис\.?)\s+(\d+)", text)
        if m:
            result.append(CaptionSnapshot(p.index, text, "figure", int(m.group(1))))
            continue
        m = re.match(r"^Таблица\s+(\d+)", text)
        if m:
            result.append(CaptionSnapshot(p.index, text, "table", int(m.group(1))))
    return result


def _guess_revisions(doc: Document) -> bool:
    xml = doc._element.xml  # noqa: SLF001
    return bool(re.search(r"w:(ins|del|moveFrom|moveTo)\b", xml))


def _has_page_numbers(doc: Document) -> bool:
    for section in doc.sections:
        for attr in ("footer", "header"):
            try:
                part = getattr(section, attr)
                xml = part._element.xml  # noqa: SLF001
                if re.search(r"instrText[^>]*>[^<]*PAGE", xml):
                    return True
            except Exception:  # noqa: BLE001
                pass
    return False


def _has_toc(doc: Document) -> bool:
    xml = doc._element.xml  # noqa: SLF001
    if re.search(r'w:docPartGallery\s+w:val="Table of Contents"', xml):
        return True
    if re.search(r"instrText[^>]*>[^<]*TOC\s", xml):
        return True
    return False


def _count_footnotes(path: Path) -> int:
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            if "word/footnotes.xml" not in zf.namelist():
                return 0
            data = zf.read("word/footnotes.xml").decode("utf-8", errors="ignore")
            total = len(re.findall(r"<w:footnote\s", data))
            return max(0, total - 2)
    except Exception:  # noqa: BLE001
        return 0


def _empty_snapshot(
    path: Path, extension: str, size: int, *, is_encrypted: bool = False,
) -> DocumentSnapshot:
    return DocumentSnapshot(
        path=path,
        extension=extension,
        size=size,
        sections=[],
        paragraphs=[],
        heading_titles=[],
        heading_snapshots=[],
        full_text="",
        comments_count=0,
        revisions_present=False,
        has_page_numbers=False,
        has_toc=False,
        footnotes_count=0,
        captions=[],
        is_encrypted=is_encrypted,
    )


def build_snapshot(file_path: str) -> DocumentSnapshot:
    path = Path(file_path)
    extension = path.suffix.lower()
    size = path.stat().st_size if path.exists() else 0

    if extension != ".docx":
        return _empty_snapshot(path, extension, size)

    try:
        doc = Document(str(path))
    except Exception:  # noqa: BLE001
        return _empty_snapshot(path, extension, size, is_encrypted=True)

    paragraphs = _paragraphs(doc)

    return DocumentSnapshot(
        path=path,
        extension=extension,
        size=size,
        sections=_section_margins(doc),
        paragraphs=paragraphs,
        heading_titles=_extract_headings(paragraphs),
        heading_snapshots=_extract_heading_snapshots(paragraphs),
        full_text="\n".join(p.text for p in paragraphs if p.text),
        comments_count=_safe_doc_attr_length(doc, "comments"),
        revisions_present=_guess_revisions(doc),
        has_page_numbers=_has_page_numbers(doc),
        has_toc=_has_toc(doc),
        footnotes_count=_count_footnotes(path),
        captions=_extract_captions(paragraphs),
        is_encrypted=False,
    )
