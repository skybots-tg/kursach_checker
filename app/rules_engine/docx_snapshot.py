from __future__ import annotations

import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from app.rules_engine.style_resolve import detect_toc_paragraph_indices, effective_alignment, walk_style_pPr

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SectionMargins:
    left_mm: float | None
    right_mm: float | None
    top_mm: float | None
    bottom_mm: float | None


_HEADING_STYLE_IDS = frozenset({
    "Heading1", "Heading2", "Heading3", "Heading4",
    "Heading5", "Heading6", "Heading7", "Heading8", "Heading9",
})


@dataclass(slots=True)
class ParagraphSnapshot:
    index: int
    text: str
    style_name: str
    style_id: str
    alignment: str | None
    first_line_indent_mm: float | None
    left_indent_mm: float | None
    line_spacing: float | None
    space_before_pt: float | None
    has_explicit_before: bool
    has_explicit_after: bool
    has_numbering: bool
    outline_level: int | None
    runs_fonts: list[str]
    runs_size_pt: list[float]
    runs_bold: list[bool | None]
    is_toc_entry: bool
    page_break_before: bool
    has_highlight: bool
    has_leading_whitespace: bool

    @property
    def is_heading(self) -> bool:
        if self.style_id in _HEADING_STYLE_IDS:
            return True
        lower = self.style_name.lower()
        if "heading" in lower or "заголов" in lower:
            return True
        return self.outline_level is not None

    @property
    def heading_level(self) -> int | None:
        if not self.is_heading:
            return None
        if self.outline_level is not None:
            return self.outline_level + 1
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
    is_corrupted: bool
    first_section_title_page: bool


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


def _resolve_line_spacing(paragraph) -> float | None:
    """Extract line spacing as a multiplier (e.g. 1.5) from any representation."""
    pformat = paragraph.paragraph_format
    raw = pformat.line_spacing
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    # Length object (exact/at-least spacing) — approximate multiplier via font size
    try:
        spacing_pt = float(raw.pt)
        base_pt = 14.0
        for run in paragraph.runs:
            if run.font and run.font.size:
                base_pt = float(run.font.size.pt)
                break
        return round(spacing_pt / base_pt, 2)
    except (AttributeError, TypeError, ValueError):
        return None


def _extract_outline_level(paragraph) -> int | None:
    for pPr in walk_style_pPr(paragraph):
        ol = pPr.find(qn("w:outlineLvl"))
        if ol is not None:
            val = ol.get(qn("w:val"))
            if val is not None:
                try:
                    lvl = int(val)
                    if lvl < 9:
                        return lvl
                except (TypeError, ValueError):
                    pass
    return None


def _has_numbering(paragraph) -> bool:
    for pPr in walk_style_pPr(paragraph):
        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            numId = numPr.find(qn("w:numId"))
            if numId is not None and numId.get(qn("w:val")) != "0":
                return True
    return False


def _detect_page_break_before(paragraph, prev_paragraph) -> bool:
    for pPr in walk_style_pPr(paragraph):
        pb = pPr.find(qn("w:pageBreakBefore"))
        if pb is not None:
            val = pb.get(qn("w:val"))
            if val is None or val in ("1", "true"):
                return True
            return False

    for run in paragraph.runs:
        for br in run._element.findall(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                return True
        if run.text and run.text.strip():
            break

    if prev_paragraph is not None:
        prev_pPr = prev_paragraph._element.find(qn("w:pPr"))
        if prev_pPr is not None:
            sectPr = prev_pPr.find(qn("w:sectPr"))
            if sectPr is not None:
                sect_type = sectPr.find(qn("w:type"))
                if sect_type is None or sect_type.get(qn("w:val")) != "continuous":
                    return True

        for run in reversed(prev_paragraph.runs):
            for br in run._element.findall(qn("w:br")):
                if br.get(qn("w:type")) == "page":
                    return True

    return False


def _first_section_title_page(doc: Document) -> bool:
    if not doc.sections:
        return False
    return bool(doc.sections[0].different_first_page_header_footer)


def _has_highlight_or_shading(paragraph) -> bool:
    for run in paragraph.runs:
        rPr = run._element.find(qn("w:rPr"))
        if rPr is None:
            continue
        hl = rPr.find(qn("w:highlight"))
        if hl is not None and hl.get(qn("w:val")) not in (None, "none"):
            return True
        shd = rPr.find(qn("w:shd"))
        if shd is not None:
            fill = shd.get(qn("w:fill"))
            if fill and fill.lower() not in ("auto", "ffffff", ""):
                return True
    pPr = paragraph._element.find(qn("w:pPr"))
    if pPr is not None:
        shd = pPr.find(qn("w:shd"))
        if shd is not None:
            fill = shd.get(qn("w:fill"))
            if fill and fill.lower() not in ("auto", "ffffff", ""):
                return True
    return False


def _paragraphs(doc: Document, toc_indices: set[int]) -> list[ParagraphSnapshot]:
    result: list[ParagraphSnapshot] = []
    all_paras = doc.paragraphs
    for idx, paragraph in enumerate(all_paras):
        raw_text = paragraph.text or ""
        text = raw_text.strip()
        pformat = paragraph.paragraph_format
        indent = _mm_from_emu(getattr(pformat.first_line_indent, "emu", None))
        left_indent = _mm_from_emu(getattr(pformat.left_indent, "emu", None))
        line_spacing = _resolve_line_spacing(paragraph)
        space_before = float(pformat.space_before.pt) if pformat.space_before is not None else None
        has_leading_ws = bool(raw_text) and raw_text[0] in (" ", "\t", "\xa0")
        prev_para = all_paras[idx - 1] if idx > 0 else None
        pb_before = _detect_page_break_before(paragraph, prev_para)
        eff_align = effective_alignment(paragraph)

        result.append(
            ParagraphSnapshot(
                index=idx,
                text=text,
                style_name=getattr(paragraph.style, "name", "") or "",
                style_id=getattr(paragraph.style, "style_id", "") or "",
                alignment=_normalize_alignment(eff_align),
                first_line_indent_mm=indent,
                left_indent_mm=left_indent,
                line_spacing=line_spacing,
                space_before_pt=space_before,
                has_explicit_before=pformat.space_before is not None,
                has_explicit_after=pformat.space_after is not None,
                has_numbering=_has_numbering(paragraph),
                outline_level=_extract_outline_level(paragraph),
                runs_fonts=_extract_run_fonts(paragraph),
                runs_size_pt=_extract_run_sizes(paragraph),
                runs_bold=_extract_run_bolds(paragraph),
                is_toc_entry=idx in toc_indices,
                page_break_before=pb_before,
                has_highlight=_has_highlight_or_shading(paragraph),
                has_leading_whitespace=has_leading_ws,
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
    path: Path, extension: str, size: int, *,
    is_encrypted: bool = False, is_corrupted: bool = False,
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
        is_corrupted=is_corrupted,
        first_section_title_page=False,
    )


def _is_encrypted_docx(path: Path) -> bool:
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            if "EncryptedPackage" in zf.namelist():
                return True
    except zipfile.BadZipFile:
        pass
    except Exception:  # noqa: BLE001
        pass
    return False


def build_snapshot(file_path: str) -> DocumentSnapshot:
    path = Path(file_path)
    extension = path.suffix.lower()

    try:
        size = path.stat().st_size if path.exists() else 0
    except OSError:
        logger.warning("Cannot stat file %s", file_path)
        size = 0

    if extension != ".docx":
        return _empty_snapshot(path, extension, size)

    if _is_encrypted_docx(path):
        logger.info("File is encrypted: %s", file_path)
        return _empty_snapshot(path, extension, size, is_encrypted=True)

    try:
        doc = Document(str(path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cannot open DOCX (corrupted?): %s — %s", file_path, exc)
        return _empty_snapshot(path, extension, size, is_corrupted=True)

    try:
        toc_indices = detect_toc_paragraph_indices(doc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to detect TOC indices: %s — %s", file_path, exc)
        toc_indices = set()

    try:
        paragraphs = _paragraphs(doc, toc_indices)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse paragraphs: %s — %s", file_path, exc)
        paragraphs = []

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
        is_corrupted=False,
        first_section_title_page=_first_section_title_page(doc),
    )
