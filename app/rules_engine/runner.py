from __future__ import annotations

from app.rules_engine.autofix import apply_safe_autofixes
from app.rules_engine.checks_advanced import (
    run_captions_checks,
    run_footnotes_checks,
    run_heading_formatting_checks,
    run_page_numbering_checks,
    run_toc_checks,
)
from app.rules_engine.checks_core import (
    run_bibliography_checks,
    run_context_extraction_checks,
    run_file_intake_checks,
    run_integrity_checks,
    run_layout_checks,
    run_objects_checks,
    run_structure_checks,
    run_typography_checks,
    run_volume_checks,
    run_work_formats_checks,
)
from app.rules_engine.docx_snapshot import build_snapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.rules_config import RulesConfig


def _summary(findings: list[Finding], size: int) -> dict:
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    fixed = sum(1 for f in findings if f.auto_fixed)
    return {"errors": errors, "warnings": warnings, "fixed": fixed, "size": size}


async def run_document_checks(file_path: str, rules: dict | None) -> dict:
    cfg = RulesConfig(rules)
    snapshot = build_snapshot(file_path)
    findings: list[Finding] = []

    if not snapshot.path.exists():
        add_finding(
            findings,
            title="Файл не найден",
            category="file",
            severity="error",
            expected="Файл должен быть доступен",
            found="Отсутствует",
            location="input",
            recommendation="Повторно загрузите файл",
        )
        return _make_result(findings, snapshot.size, cfg, None)

    if snapshot.is_encrypted:
        add_finding(
            findings,
            title="Файл зашифрован",
            category="integrity",
            severity="error",
            expected="Документ не защищён паролем",
            found="Документ защищён паролем или повреждён",
            location="файл",
            recommendation="Снимите защиту и загрузите файл заново",
        )
        return _make_result(findings, snapshot.size, cfg, None)

    run_file_intake_checks(snapshot, cfg, findings)

    if snapshot.extension == ".docx":
        run_integrity_checks(snapshot, cfg, findings)
        run_context_extraction_checks(snapshot, cfg, findings)
        run_work_formats_checks(snapshot, cfg, findings)
        run_layout_checks(snapshot, cfg, findings)
        run_typography_checks(snapshot, cfg, findings)
        run_heading_formatting_checks(snapshot, cfg, findings)
        run_structure_checks(snapshot, cfg, findings)
        run_volume_checks(snapshot, cfg, findings)
        run_bibliography_checks(snapshot, cfg, findings)
        run_objects_checks(snapshot, cfg, findings)
        run_page_numbering_checks(snapshot, cfg, findings)
        run_toc_checks(snapshot, cfg, findings)
        run_footnotes_checks(snapshot, cfg, findings)
        run_captions_checks(snapshot, cfg, findings)

    autofix_output_path: str | None = None
    if snapshot.extension == ".docx":
        autofix = apply_safe_autofixes(file_path, rules, findings)
        autofix_output_path = autofix.output_file_path

    if not findings:
        add_finding(
            findings,
            title="Проверка оформления",
            category="summary",
            severity="advice",
            expected="Соответствие базовым правилам",
            found="Нарушений не обнаружено",
            location="документ",
            recommendation="Можно переходить к следующему этапу",
        )

    return _make_result(findings, snapshot.size, cfg, autofix_output_path)


def _make_result(
    findings: list[Finding], size: int, cfg: RulesConfig, output_path: str | None,
) -> dict:
    return {
        "summary": _summary(findings, size),
        "findings": [x.to_dict() for x in findings],
        "rules_meta": {"blocks_count": cfg.blocks_count()},
        "output_docx_path": output_path,
    }
