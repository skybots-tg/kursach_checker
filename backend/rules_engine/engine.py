from __future__ import annotations

"""
Минимальный исполняющий движок проверок.

Задача этого модуля — связать:
- TemplateRulesConfig (универсальный конфиг шаблона/ГОСТа);
- разобранный документ (будет добавлен позже);
- формат отчёта CheckReport.

Сейчас реализован упрощённый вариант, который:
- принимает конфиг и «сырые» байты файла;
- возвращает пустой отчёт с нулевыми счётчиками.

Это позволяет уже собрать end‑to‑end pipeline (очередь → отчёт → Mini App),
а затем постепенно наращивать набор реальных проверок, не меняя API.
"""

from backend.rules_engine.findings import CheckReport
from backend.rules_engine.schemas import TemplateRulesConfig
from backend.rules_engine.docx_utils import load_docx_from_bytes
from backend.rules_engine.checks_integrity import run_integrity_checks
from backend.rules_engine.checks_layout_typography import run_layout_and_typography_checks
from backend.rules_engine.checks_structure_volume import run_structure_bibliography_volume_checks
from backend.rules_engine.checks_extraction import run_extraction


async def run_checks(
    *,
    template_version_id: int,
    rules: TemplateRulesConfig,
    file_bytes: bytes,
) -> CheckReport:
    """
    Выполняет проверки документа по заданному конфигу.

    Минимально реализованы группы:
    - integrity / objects;
    - page layout / typography;
    - structure / bibliography / volume.
    """
    loaded = load_docx_from_bytes(file_bytes)

    findings = []

    # Извлечение контекста (курс, количество авторов) для условных правил.
    extracted_ctx, extraction_findings = run_extraction(rules, loaded)
    findings.extend(extraction_findings)

    findings.extend(run_integrity_checks(rules, loaded))
    findings.extend(run_layout_and_typography_checks(rules, loaded))
    findings.extend(
        run_structure_bibliography_volume_checks(
            rules,
            loaded,
            course_year=extracted_ctx.course_year,
            authors_count=extracted_ctx.authors_count,
        )
    )

    summary_errors = sum(1 for f in findings if f.severity == "error")
    summary_warnings = sum(1 for f in findings if f.severity == "warning")
    summary_autofixed = sum(1 for f in findings if f.auto_fixed)

    return CheckReport(
        template_profile_id=rules.profile_id,
        template_version_id=template_version_id,
        summary_errors=summary_errors,
        summary_warnings=summary_warnings,
        summary_autofixed=summary_autofixed,
        findings=findings,
    )





