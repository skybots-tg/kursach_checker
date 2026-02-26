from __future__ import annotations

"""
Проверки структуры документа, списка литературы и объёма.
"""

from collections import Counter
from typing import Sequence

from backend.rules_engine.docx_utils import LoadedDocx, count_chars_between_titles
from backend.rules_engine.findings import Finding, FindingLocation
from backend.rules_engine.schemas import FormatConfig, SectionConfig, TemplateRulesConfig


def run_structure_bibliography_volume_checks(
    rules: TemplateRulesConfig,
    loaded: LoadedDocx,
    *,
    course_year: int | None,
    authors_count: int | None,
) -> list[Finding]:
    findings: list[Finding] = []

    # Для минимального варианта берём первый формат как основной.
    active_format: FormatConfig | None = rules.formats[0] if rules.formats else None

    if active_format is not None:
        findings.extend(_check_required_sections(active_format, loaded))

    if active_format is not None and active_format.structure.bibliography is not None:
        findings.extend(_check_bibliography(active_format, loaded))

    if rules.volume is not None and active_format is not None:
        findings.extend(
            _check_volume(
                rules,
                active_format,
                loaded,
                course_year=course_year,
                authors_count=authors_count,
            )
        )

    return findings


def _find_section_indices_by_titles(
    loaded: LoadedDocx,
    titles_any_of: Sequence[str],
) -> list[int]:
    result: list[int] = []
    targets = {t.strip().lower() for t in titles_any_of}
    for idx, p in enumerate(loaded.doc.paragraphs):
        title = (p.text or "").strip().lower()
        if not title:
            continue
        if title in targets:
            result.append(idx)
    return result


def _check_required_sections(format_cfg: FormatConfig, loaded: LoadedDocx) -> list[Finding]:
    findings: list[Finding] = []

    for section in format_cfg.structure.required_sections_in_order:
        findings.extend(_check_single_section(section, loaded))

    return findings


def _check_single_section(
    section: SectionConfig,
    loaded: LoadedDocx,
) -> list[Finding]:
    findings: list[Finding] = []

    titles = section.titles_any_of or []
    if section.detect and section.detect.titles_any_of:
        titles = list(set(titles) | set(section.detect.titles_any_of))

    if not titles and not section.detect:
        return findings

    indices = _find_section_indices_by_titles(loaded, titles) if titles else []

    required = section.required if section.required is not None else True

    if required and not indices:
        findings.append(
            Finding(
                rule_id=f"structure.section.{section.id}",
                title=f"В документе не найден раздел «{titles[0] if titles else section.id}»",
                category="structure",
                severity="error",
                expected="Раздел должен присутствовать в документе согласно шаблону.",
                actual="Раздел не найден среди заголовков документа.",
                recommendation="Проверьте, что раздел присутствует и его заголовок написан без ошибок.",
                location=FindingLocation(section_id=section.id),
            )
        )

    return findings


def _check_bibliography(format_cfg: FormatConfig, loaded: LoadedDocx) -> list[Finding]:
    findings: list[Finding] = []
    bcfg = format_cfg.structure.bibliography
    assert bcfg is not None

    # Находим раздел списка литературы.
    bib_section = None
    for section in format_cfg.structure.required_sections_in_order:
        if section.id == "bibliography":
            bib_section = section
            break

    if not bib_section or not (bib_section.titles_any_of or (bib_section.detect and bib_section.detect.titles_any_of)):
        return findings

    titles = bib_section.titles_any_of or bib_section.detect.titles_any_of or []
    indices = _find_section_indices_by_titles(loaded, titles)
    if not indices:
        return findings

    start_idx = indices[0] + 1

    # Считаем количество непустых абзацев после заголовка до следующего крупного заголовка.
    count_sources = 0
    for p in loaded.doc.paragraphs[start_idx:]:
        text = (p.text or "").strip()
        if not text:
            continue
        # Грубое эвристическое ограничение: если начинается новый раздел типа "Приложения",
        # то останавливаемся.
        if text.lower().startswith("приложени"):
            break
        count_sources += 1

    if bcfg.min_total_sources is not None and count_sources < bcfg.min_total_sources:
        findings.append(
            Finding(
                rule_id="bibliography.min_total_sources",
                title="Недостаточно источников в списке литературы",
                category="bibliography",
                severity="warning",
                expected=f"Не менее {bcfg.min_total_sources} источников.",
                actual=f"Обнаружено примерно {count_sources} источников.",
                recommendation="Добавьте недостающие источники согласно методическим требованиям.",
                location=FindingLocation(section_id="bibliography"),
            )
        )

    # Эвристика по "свежим" и иностранным источникам пока не реализована.
    return findings


def _check_volume(
    rules: TemplateRulesConfig,
    format_cfg: FormatConfig,
    loaded: LoadedDocx,
    *,
    course_year: int | None,
    authors_count: int | None,
) -> list[Finding]:
    findings: list[Finding] = []
    vcfg = rules.volume
    assert vcfg is not None

    # Подсчёт символов между заданными разделами.
    volume_chars = count_chars_between_titles(
        loaded.doc,
        start_titles=vcfg.include_from_section_any_of,
        stop_titles=vcfg.stop_before_section_any_of,
    )

    author_sheets = volume_chars / float(vcfg.author_sheet_chars_with_spaces)

    # Пытаемся найти правило, соответствующее курсу и количеству авторов.
    applicable_rules = [r for r in vcfg.rules if r.format == format_cfg.name]
    if not applicable_rules:
        return findings

    matched_rule = None
    if course_year is not None and authors_count is not None:
        for r in applicable_rules:
            if r.course_year != course_year:
                continue
            if r.authors is not None and r.authors != authors_count:
                continue
            if r.authors_in is not None and authors_count not in r.authors_in:
                continue
            matched_rule = r
            break

    # Если конкретное правило не найдено или контекст не определён,
    # используем минимальное требование по формату.
    if matched_rule is None:
        matched_rule = min(applicable_rules, key=lambda x: x.min_author_sheets)

    min_required = matched_rule.min_author_sheets

    if author_sheets < min_required:
        findings.append(
            Finding(
                rule_id="volume.min_author_sheets",
                title="Недостаточный объём работы",
                category="volume",
                severity=matched_rule.if_unknown_course_or_authors_severity or "warning",
                expected=f"Не менее {min_required:.2f} авторских листов.",
                actual=f"Ориентировочно {author_sheets:.2f} авторских листов.",
                recommendation="Увеличьте объём основной части работы согласно требованиям вуза.",
                location=FindingLocation(),
            )
        )

    return findings



