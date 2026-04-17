from __future__ import annotations

from pydantic import BaseModel, Field


class AutofixRuleInfo(BaseModel):
    """Описание одного типа автоисправления."""

    rule_id: str
    title: str
    description: str
    safe: bool = True
    default_enabled: bool = True


class AutofixDefaultsIn(BaseModel):
    """Глобальные дефолты автоисправлений (перезаписываются шаблоном)."""

    enabled: bool = True
    normalize_alignment: bool = True
    normalize_line_spacing: bool = True
    normalize_first_line_indent: bool = True
    normalize_spacing_before_after: bool = True
    normalize_font: bool = True
    normalize_margins: bool = False
    normalize_table_width: bool = True
    normalize_headings: bool = True
    normalize_font_color: bool = True
    remove_italic: bool = True
    normalize_list_indent: bool = True
    normalize_list_markers: bool = True
    normalize_dashes: bool = True
    remove_caption_trailing_dot: bool = True
    space_before_pt: float = Field(0.0, ge=0)
    space_after_pt: float = Field(0.0, ge=0)


class AutofixSafetyLimits(BaseModel):
    """Пределы безопасности — что нельзя трогать."""

    skip_headings: bool = True
    skip_tables: bool = True
    skip_toc: bool = True
    skip_footnotes: bool = False
    skip_margin_normalization: bool = True
    max_changes_per_document: int = Field(500, ge=1)


class AutofixGlobalConfig(BaseModel):
    defaults: AutofixDefaultsIn = Field(default_factory=AutofixDefaultsIn)
    safety_limits: AutofixSafetyLimits = Field(default_factory=AutofixSafetyLimits)


class AutofixStatsOut(BaseModel):
    total_checks_with_autofix: int
    total_autofixed_items: int
    avg_fixes_per_check: float


AUTOFIX_RULES_CATALOG: list[AutofixRuleInfo] = [
    AutofixRuleInfo(
        rule_id="normalize_alignment",
        title="Выравнивание абзацев",
        description="Устанавливает выравнивание по ширине для абзацев основного текста",
    ),
    AutofixRuleInfo(
        rule_id="normalize_line_spacing",
        title="Межстрочный интервал",
        description="Приводит межстрочный интервал к значению из шаблона (по умолчанию 1,5)",
    ),
    AutofixRuleInfo(
        rule_id="normalize_first_line_indent",
        title="Отступ первой строки",
        description="Устанавливает красную строку по значению из шаблона (по умолчанию 12,5 мм)",
    ),
    AutofixRuleInfo(
        rule_id="normalize_spacing_before_after",
        title="Интервалы до/после абзаца",
        description="Устанавливает интервалы «до» и «после» для абзацев основного текста",
    ),
    AutofixRuleInfo(
        rule_id="normalize_font",
        title="Шрифт и кегль",
        description="Приводит шрифт и размер к значениям из шаблона (Times New Roman 14 по умолчанию)",
    ),
    AutofixRuleInfo(
        rule_id="normalize_margins",
        title="Поля страницы",
        description="Нормализует поля страницы по ГОСТу. Отключено по умолчанию — может сломать вёрстку",
        safe=False,
        default_enabled=False,
    ),
    AutofixRuleInfo(
        rule_id="normalize_table_width",
        title="Ширина таблиц",
        description="Приводит ширину таблиц к области текста при переполнении",
        safe=False,
        default_enabled=False,
    ),
    AutofixRuleInfo(
        rule_id="normalize_headings",
        title="Форматирование заголовков",
        description="Нормализует шрифт и кегль заголовков по шаблону",
        safe=False,
        default_enabled=False,
    ),
    AutofixRuleInfo(
        rule_id="normalize_font_color",
        title="Цвет текста",
        description="Устанавливает чёрный цвет для всего текста, включая заголовки и оглавление",
    ),
    AutofixRuleInfo(
        rule_id="remove_italic",
        title="Удаление курсива",
        description="Убирает курсивное начертание из всего текста по ГОСТ",
    ),
    AutofixRuleInfo(
        rule_id="normalize_list_indent",
        title="Отступы списков",
        description="Убирает красную строку и лишний отступ у элементов перечислений",
    ),
    AutofixRuleInfo(
        rule_id="normalize_list_markers",
        title="Маркеры списков",
        description="Заменяет маркеры-кружочки и прочие символы на тире",
    ),
    AutofixRuleInfo(
        rule_id="normalize_dashes",
        title="Длинные тире",
        description="Заменяет длинные тире на короткие в тексте (кроме перечислений)",
    ),
    AutofixRuleInfo(
        rule_id="remove_caption_trailing_dot",
        title="Точка в подписях",
        description="Убирает завершающую точку в подписях рисунков и таблиц",
    ),
    AutofixRuleInfo(
        rule_id="normalize_toc_heading",
        title="Оформление заголовка «Содержание»",
        description=(
            "Центрирует заголовок «Содержание»/«Оглавление», убирает жирное "
            "выделение и подчёркивание"
        ),
    ),
    AutofixRuleInfo(
        rule_id="ensure_subheading_spacing",
        title="Пустая строка перед подзаголовками",
        description=(
            "Добавляет один пустой абзац перед подразделами (1.1, 1.2 …) "
            "внутри главы, сохраняя разрыв страницы перед самими главами"
        ),
    ),
    AutofixRuleInfo(
        rule_id="heading_level2plus_center",
        title="Подзаголовки по центру",
        description=(
            "Выравнивает заголовки подразделов (1.1, 1.2 …) по центру и "
            "убирает у них красную строку"
        ),
    ),
    AutofixRuleInfo(
        rule_id="fix_caption_positions",
        title="Позиция подписей рисунков и таблиц",
        description=(
            "Переносит подпись «Рисунок N …» под изображение и центрирует её; "
            "подпись «Таблица N …» ставит над таблицей и выравнивает по левому краю"
        ),
    ),
]

NOT_AUTOFIXABLE_INFO: list[AutofixRuleInfo] = [
    AutofixRuleInfo(
        rule_id="structure_sections",
        title="Структура разделов",
        description="Автоисправление структуры невозможно — только подсказки",
        safe=False,
        default_enabled=False,
    ),
    AutofixRuleInfo(
        rule_id="bibliography_gost",
        title="Библиография по ГОСТ",
        description="Формат библиографии слишком сложен для автоисправления",
        safe=False,
        default_enabled=False,
    ),
    AutofixRuleInfo(
        rule_id="foreign_recent_sources",
        title="Иноязычные/свежие источники",
        description="Содержание источников не подлежит автоматическому изменению",
        safe=False,
        default_enabled=False,
    ),
    AutofixRuleInfo(
        rule_id="complex_objects",
        title="Таблицы, формулы, рисунки",
        description="Сложные объекты не модифицируются из соображений безопасности",
        safe=False,
        default_enabled=False,
    ),
]
