from pydantic import BaseModel, Field


class RuleBlock(BaseModel):
    key: str
    title: str
    enabled: bool = True
    severity: str = Field(default="error", pattern="^(error|warning|advice|off)$")
    params: dict = Field(default_factory=dict)


class TemplateRules(BaseModel):
    # Универсальный расширяемый набор блоков, можно добавлять новые ключи без миграций схемы БД
    blocks: list[RuleBlock] = Field(default_factory=list)


DEFAULT_TEMPLATE_BLOCKS: list[RuleBlock] = [
    RuleBlock(key="passport", title="Паспорт шаблона", severity="off"),
    RuleBlock(
        key="file_intake",
        title="Приём файлов",
        severity="error",
        params={
            "allowed_extensions": ["doc", "docx"],
            "max_size_mb": 20,
            "doc_policy": "convert",
        },
    ),
    RuleBlock(
        key="context_extraction",
        title="Контекст работы",
        severity="warning",
        params={
            "detect_course_year": True,
            "detect_authors_count": True,
            "course_year_regex": "(?i)\\b([2-6])\\s*курс\\b",
            "authors_labels": ["Автор", "Автор(ы)", "Студент", "Студент(ы)", "Выполнил", "Выполнили"],
        },
    ),
    RuleBlock(
        key="work_formats",
        title="Форматы и групповая работа",
        severity="error",
        params={
            "allowed_formats": ["academic", "project_creative"],
            "max_authors": {"academic": 2, "project_creative": 3},
            "allowed_for_course_years": {"academic": [2, 3], "project_creative": [3]},
        },
    ),
    RuleBlock(
        key="structure",
        title="Структура и разделы",
        severity="error",
        params={
            "required_sections_in_order": [
                {"id": "introduction", "titles_any_of": ["введение"]},
                {"id": "main_body", "titles_any_of": ["основная часть"]},
                {"id": "conclusion", "titles_any_of": ["заключение"]},
                {
                    "id": "bibliography",
                    "titles_any_of": [
                        "список использованных источников и литературы",
                        "список использованных источников",
                        "список литературы",
                    ],
                },
            ]
        },
    ),
    RuleBlock(
        key="volume",
        title="Объём и подсчёт",
        severity="warning",
        params={"author_sheet_chars_with_spaces": 40000, "min_author_sheets_default": 0.5},
    ),
    RuleBlock(
        key="bibliography",
        title="Источники",
        severity="warning",
        params={"min_total_sources": 20, "require_foreign_sources": True, "recent_window_years_max": 10},
    ),
    RuleBlock(
        key="layout",
        title="Страница и поля",
        severity="warning",
        params={"margins_mm": {"top": 20, "bottom": 25, "left": 30, "right": 15}, "tolerance_mm": 1},
    ),
    RuleBlock(
        key="typography",
        title="Основной текст",
        severity="warning",
        params={"body": {"font": "Times New Roman", "size_pt": 14, "line_spacing": 1.5, "first_line_indent_mm": 12.5}},
    ),
    RuleBlock(
        key="footnotes",
        title="Сноски",
        severity="warning",
        params={"required": False, "font": "Times New Roman", "size_pt": 10},
    ),
    RuleBlock(
        key="objects",
        title="Таблицы/рисунки/объекты",
        severity="warning",
        params={"forbid_linked_media": True, "require_embedded_objects": True},
    ),
    RuleBlock(
        key="integrity",
        title="Техническая чистота",
        severity="error",
        params={"forbid_track_changes": True, "forbid_comments": True, "forbid_password_protection": True},
    ),
    RuleBlock(
        key="autofix",
        title="Автоисправления",
        severity="advice",
        params={
            "normalize_alignment": True,
            "normalize_line_spacing": True,
            "normalize_first_line_indent": True,
            "normalize_spacing_before_after": True,
            "normalize_font": True,
            "space_before_pt": 0,
            "space_after_pt": 0,
        },
    ),
    RuleBlock(key="reporting", title="Отчёт и строгость", severity="advice"),
    RuleBlock(key="demo_test", title="Тестирование на примере", severity="off"),
]
