from __future__ import annotations

"""
Извлечение контекста из документа:
- курс обучения (course_year);
- количество авторов (authors_count).

Эти значения используются условными правилами (структура, объём и т.п.).
"""

import re
from dataclasses import dataclass
from typing import Any

from backend.rules_engine.docx_utils import LoadedDocx
from backend.rules_engine.findings import Finding, FindingLocation
from backend.rules_engine.schemas import ExtractionConfig, TemplateRulesConfig


@dataclass
class ExtractedContext:
    course_year: int | None = None
    authors_count: int | None = None


def run_extraction(
    rules: TemplateRulesConfig,
    loaded: LoadedDocx,
) -> tuple[ExtractedContext, list[Finding]]:
    findings: list[Finding] = []
    ctx = ExtractedContext()

    if rules.extraction is None:
        return ctx, findings

    text_first_page = _get_first_page_text(loaded)
    text_full = _get_full_text(loaded)

    ctx.course_year, f_course = _extract_course_year(rules.extraction, text_first_page, text_full)
    findings.extend(f_course)

    ctx.authors_count, f_auth = _extract_authors_count(rules.extraction, text_first_page, text_full)
    findings.extend(f_auth)

    return ctx, findings


def _get_first_page_text(loaded: LoadedDocx) -> str:
    # python-docx не даёт точной разбивки по страницам, поэтому для титульного листа
    # берём первые несколько абзацев.
    parts: list[str] = []
    for p in loaded.doc.paragraphs[:40]:
        if p.text:
            parts.append(p.text)
    return "\n".join(parts)


def _get_full_text(loaded: LoadedDocx) -> str:
    parts: list[str] = []
    for p in loaded.doc.paragraphs:
        if p.text:
            parts.append(p.text)
    return "\n".join(parts)


def _extract_course_year(
    cfg: ExtractionConfig,
    text_first_page: str,
    text_full: str,
) -> tuple[int | None, list[Finding]]:
    findings: list[Finding] = []

    if cfg.course_year is None:
        return None, findings

    text = ""
    if "first_page" in cfg.course_year.search_scopes:
        text += text_first_page + "\n"
    if "whole_document" in cfg.course_year.search_scopes:
        text += text_full

    for pattern in cfg.course_year.regex_any_of:
        try:
            regex = re.compile(pattern)
        except re.error:
            continue
        m = regex.search(text)
        if m:
            try:
                value = int(m.group(1))
            except (IndexError, ValueError):
                continue
            return value, findings

    if cfg.course_year.if_not_found_severity:
        findings.append(
            Finding(
                rule_id="extraction.course_year.not_found",
                title="Не удалось определить курс из документа",
                category="structure",
                severity=cfg.course_year.if_not_found_severity,
                expected="Курс должен быть указан на титульном листе или в начале документа.",
                actual="Шаблонные фразы про курс не найдены.",
                recommendation="Убедитесь, что курс указан, или задайте его вручную в интерфейсе.",
                location=FindingLocation(),
            )
        )

    return None, findings


def _extract_authors_count(
    cfg: ExtractionConfig,
    text_first_page: str,
    text_full: str,
) -> tuple[int | None, list[Finding]]:
    findings: list[Finding] = []

    if cfg.authors_count is None:
        return None, findings

    text = ""
    if "first_page" in cfg.authors_count.search_scopes:
        text += text_first_page + "\n"
    if "whole_document" in cfg.authors_count.search_scopes:
        text += text_full

    labels_lower = [l.lower() for l in cfg.authors_count.labels_any_of]

    for line in text.splitlines():
        line_norm = line.strip()
        if not line_norm:
            continue
        lower = line_norm.lower()
        if any(label in lower for label in labels_lower):
            # Простейшая эвристика: берём часть после двоеточия/тире и считаем имена,
            # разделённые запятыми или «и».
            tail = line_norm
            for sep in (":", "—", "-"):
                if sep in tail:
                    tail = tail.split(sep, 1)[1]
                    break
            # Разделяем по запятым и союзу «и».
            parts = re.split(r",| и ", tail)
            names = [p.strip() for p in parts if p.strip()]
            if names:
                return len(names), findings

    if cfg.authors_count.if_not_found_severity:
        findings.append(
            Finding(
                rule_id="extraction.authors_count.not_found",
                title="Не удалось определить количество авторов",
                category="structure",
                severity=cfg.authors_count.if_not_found_severity,
                expected="Количество авторов должно быть указано на титульном листе.",
                actual="Метки “Автор/Студент/Выполнил” не найдены или не распознаны.",
                recommendation="Убедитесь, что на титульном листе явно указаны все авторы.",
                location=FindingLocation(),
            )
        )

    return None, findings





