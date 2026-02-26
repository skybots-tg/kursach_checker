from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


Severity = Literal["error", "warning", "info"]


class IntegrityChecks(BaseModel):
    """Техническая чистота документа."""

    forbid_track_changes: bool = True
    forbid_comments: bool = True
    forbid_password_protection: bool = True
    forbid_linked_media: bool = True


class InputConfig(BaseModel):
    """
    Настройки приёма файлов.

    Держим это отдельно от собственно проверок, чтобы можно было легко расширять
    (максимальный размер, политика по DOC/PDF и т.п.), не трогая rules‑engine.
    """

    allowed_file_extensions: list[str] = Field(default_factory=list)


class ExtractionCourseYear(BaseModel):
    regex_any_of: list[str] = Field(default_factory=list)
    search_scopes: list[Literal["first_page", "whole_document"]] = Field(default_factory=list)
    if_not_found_severity: Severity | None = Field(default="warning")


class ExtractionAuthorsCount(BaseModel):
    labels_any_of: list[str] = Field(default_factory=list)
    search_scopes: list[Literal["first_page", "whole_document"]] = Field(default_factory=list)
    if_not_found_severity: Severity | None = Field(default="warning")


class ExtractionConfig(BaseModel):
    course_year: ExtractionCourseYear | None = None
    authors_count: ExtractionAuthorsCount | None = None


class ChapterRules(BaseModel):
    min_chapters: int | None = None
    min_paragraphs_per_chapter: int | None = None


class SectionDetection(BaseModel):
    kind: Literal["title", "first_page_contains_any"] | None = None
    patterns_any_of: list[str] | None = None
    titles_any_of: list[str] | None = None


class SectionConfig(BaseModel):
    id: str
    detect: SectionDetection | None = None
    titles_any_of: list[str] | None = None
    required: bool | None = None
    required_if_authors_min: int | None = None
    chapter_rules: ChapterRules | None = None


class BibliographyConfig(BaseModel):
    min_total_sources: int | None = None
    require_foreign_sources: bool = False
    recent_min_share: float | None = None
    recent_window_years_max: int | None = None


class FormatStructureConfig(BaseModel):
    required_sections_in_order: list[SectionConfig] = Field(default_factory=list)
    bibliography: BibliographyConfig | None = None


class FormatConfig(BaseModel):
    name: str
    allowed_for_course_years: list[int] = Field(default_factory=list)
    group_work_allowed: bool = False
    group_work_max_authors: int | None = None
    structure: FormatStructureConfig


class VolumeRule(BaseModel):
    format: str
    course_year: int | None = None
    authors: int | None = None
    authors_in: list[int] | None = None
    min_author_sheets: float
    if_unknown_course_or_authors_severity: Severity | None = None


class VolumeConfig(BaseModel):
    unit: Literal["author_sheet"] = "author_sheet"
    author_sheet_chars_with_spaces: int = 40000
    include_spaces: bool = True
    include_from_section_any_of: list[str] = Field(default_factory=list)
    stop_before_section_any_of: list[str] = Field(default_factory=list)
    rules: list[VolumeRule] = Field(default_factory=list)


class PageLayoutConfig(BaseModel):
    page_size: Literal["A4"] = "A4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    margins_mm: dict[str, int] = Field(default_factory=dict)
    tolerance_mm: int = 1


class TypographyAreaConfig(BaseModel):
    font: str
    size_pt: int
    line_spacing: float
    alignment: Literal["left", "right", "center", "justify"]
    first_line_indent_mm: float


class TypographyConfig(BaseModel):
    body: TypographyAreaConfig
    footnotes: TypographyAreaConfig | None = None


class ObjectsConfig(BaseModel):
    require_embedded_objects: bool = True


class TemplateRulesConfig(BaseModel):
    """Универсальный конфиг шаблона/ГОСТа (rules_json в БД)."""

    model_config = ConfigDict(extra="allow")

    profile_id: str
    document_kind: str
    # Человеко‑читаемое описание/источник методички (для админки).
    document_label: str | None = None
    # Блок настроек приёма файлов (расширяемый).
    input: InputConfig | None = None
    integrity: IntegrityChecks = Field(default_factory=IntegrityChecks)
    extraction: ExtractionConfig | None = None
    formats: list[FormatConfig] = Field(default_factory=list)
    volume: VolumeConfig | None = None
    layout: PageLayoutConfig | None = None
    typography: TypographyConfig | None = None
    objects: ObjectsConfig | None = None


