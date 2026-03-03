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
    RuleBlock(key="file_intake", title="Приём файлов"),
    RuleBlock(key="context_extraction", title="Контекст работы"),
    RuleBlock(key="work_formats", title="Форматы и групповая работа"),
    RuleBlock(key="structure", title="Структура и разделы"),
    RuleBlock(key="volume", title="Объём и подсчёт"),
    RuleBlock(key="bibliography", title="Источники"),
    RuleBlock(key="layout", title="Страница и поля"),
    RuleBlock(key="typography", title="Основной текст"),
    RuleBlock(key="footnotes", title="Сноски"),
    RuleBlock(key="objects", title="Таблицы/рисунки/объекты"),
    RuleBlock(key="integrity", title="Техническая чистота"),
    RuleBlock(key="reporting", title="Отчёт и строгость"),
    RuleBlock(key="demo_test", title="Тестирование на примере", severity="off"),
]

