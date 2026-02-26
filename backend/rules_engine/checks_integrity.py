from __future__ import annotations

"""
Проверки технической чистоты файла и объектов:
- режим правок;
- комментарии;
- защита паролем;
- внешние/невстроенные объекты.
"""

from backend.rules_engine.docx_utils import (
    LoadedDocx,
    xml_has_comments,
    xml_has_linked_media,
    xml_has_password_protection,
    xml_has_track_changes,
)
from backend.rules_engine.findings import Category, Finding, FindingLocation
from backend.rules_engine.schemas import TemplateRulesConfig


def run_integrity_checks(rules: TemplateRulesConfig, loaded: LoadedDocx) -> list[Finding]:
    findings: list[Finding] = []
    cfg = rules.integrity

    if cfg.forbid_track_changes and xml_has_track_changes(loaded.main_xml):
        findings.append(
            Finding(
                rule_id="integrity.track_changes",
                title="Включён режим правок",
                category="integrity",
                severity="error",
                expected="В документе должен быть отключён режим правок (track changes).",
                actual="Обнаружены вставки/удаления или маркеры track revisions.",
                recommendation="Примите или отклоните все правки и отключите режим правок в Word.",
                location=FindingLocation(),
            )
        )

    if cfg.forbid_comments and xml_has_comments(loaded.main_xml, loaded.comments_xml):
        findings.append(
            Finding(
                rule_id="integrity.comments",
                title="В документе есть комментарии",
                category="integrity",
                severity="error",
                expected="В документе не должно быть комментариев рецензентов/руководителя.",
                actual="Найдены элементы комментариев в тексте.",
                recommendation="Удалите все комментарии перед сдачей работы.",
                location=FindingLocation(),
            )
        )

    if cfg.forbid_password_protection and xml_has_password_protection(loaded.settings_xml):
        findings.append(
            Finding(
                rule_id="integrity.password_protection",
                title="Документ защищён от редактирования",
                category="integrity",
                severity="error",
                expected="Документ не должен быть защищён паролем или ограничением редактирования.",
                actual="В настройках документа найдена защита редактирования.",
                recommendation="Снимите защиту с документа перед загрузкой на проверку.",
                location=FindingLocation(),
            )
        )

    if cfg.forbid_linked_media and xml_has_linked_media(loaded.main_xml):
        findings.append(
            Finding(
                rule_id="objects.linked_media",
                title="Обнаружены внешние объекты/картинки по ссылке",
                category="objects",
                severity="warning",
                expected="Все изображения и объекты должны быть встроены в документ.",
                actual="Найдены ссылки на внешние медиа‑объекты.",
                recommendation="Вставьте изображения и объекты напрямую в документ (Insert → Picture / Object).",
                location=FindingLocation(),
            )
        )

    return findings



