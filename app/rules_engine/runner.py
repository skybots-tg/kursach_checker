from __future__ import annotations

import logging
from typing import Callable

from app.rules_engine.autofix import apply_safe_autofixes
from app.rules_engine.checks_advanced import (
    run_captions_checks,
    run_footnotes_checks,
    run_heading_formatting_checks,
    run_page_numbering_checks,
    run_section_breaks_checks,
    run_toc_checks,
)
from app.rules_engine.checks_content import (
    run_bibliography_checks,
    run_list_formatting_checks,
    run_objects_checks,
    run_text_cleanliness_checks,
)
from app.rules_engine.checks_headings import (
    run_heading_numbering_checks,
    run_heading_semantics_checks,
)
from app.rules_engine.checks_core import (
    run_context_extraction_checks,
    run_file_intake_checks,
    run_integrity_checks,
    run_layout_checks,
    run_structure_checks,
    run_typography_checks,
    run_volume_checks,
    run_work_formats_checks,
)
from app.rules_engine.docx_snapshot import build_snapshot
from app.rules_engine.findings import Finding, add_finding
from app.rules_engine.rules_config import RulesConfig

logger = logging.getLogger(__name__)

_CHECK_NAME_RU: dict[str, str] = {
    "file_intake": "формат файла",
    "integrity": "целостность документа",
    "context_extraction": "определение курса и авторов",
    "work_formats": "формат работы",
    "layout": "поля и страница",
    "typography": "шрифт и абзацы",
    "heading_formatting": "заголовки",
    "heading_semantics": "семантика заголовков",
    "heading_numbering": "нумерация заголовков",
    "structure": "структура работы",
    "volume": "объём текста",
    "bibliography": "список источников",
    "objects": "таблицы и рисунки",
    "page_numbering": "нумерация страниц",
    "section_breaks": "разделы с новой страницы",
    "toc": "оглавление",
    "footnotes": "сноски",
    "captions": "подписи к объектам",
    "text_cleanliness": "посторонние символы",
    "list_formatting": "оформление списков",
}

CheckFunc = Callable[..., None]


def _summary(findings: list[Finding], size: int) -> dict:
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    fixed = sum(1 for f in findings if f.auto_fixed)
    return {"errors": errors, "warnings": warnings, "fixed": fixed, "size": size}


def _run_check_safe(
    name: str,
    func: CheckFunc,
    snapshot: object,
    cfg: RulesConfig,
    findings: list[Finding],
    check_errors: list[str],
) -> None:
    try:
        func(snapshot, cfg, findings)
    except Exception:
        logger.exception("Check '%s' crashed for %s", name, snapshot.path)  # type: ignore[attr-defined]
        label = _CHECK_NAME_RU.get(name, name)
        check_errors.append(f"Проверка «{label}» завершилась с внутренней ошибкой")
        add_finding(
            findings,
            title=f"Внутренняя ошибка: {label}",
            category="internal",
            severity="warning",
            expected="Проверка выполняется без ошибок",
            found=f"Проверка «{label}» не выполнена из-за внутренней ошибки",
            location="система",
            recommendation="Сообщите администратору. Остальные проверки продолжены.",
        )


async def run_document_checks(
    file_path: str, rules: dict | None,
    admin_autofix_config: dict | None = None,
) -> dict:
    logger.info("Starting document checks: %s", file_path)
    cfg = RulesConfig(rules)
    check_errors: list[str] = []

    try:
        snapshot = build_snapshot(file_path)
    except Exception:
        logger.exception("Failed to build snapshot for %s", file_path)
        findings: list[Finding] = []
        add_finding(
            findings,
            title="Ошибка чтения файла",
            category="file",
            severity="error",
            expected="Файл успешно прочитан",
            found="Не удалось прочитать файл",
            location="input",
            recommendation="Проверьте файл и загрузите заново",
        )
        return _make_result(findings, 0, cfg, None, check_errors)

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
        return _make_result(findings, snapshot.size, cfg, None, check_errors)

    if snapshot.is_encrypted:
        add_finding(
            findings,
            title="Файл зашифрован",
            category="integrity",
            severity="error",
            expected="Документ не защищён паролем",
            found="Документ защищён паролем",
            location="файл",
            recommendation="Снимите защиту паролем и загрузите файл заново",
        )
        return _make_result(findings, snapshot.size, cfg, None, check_errors)

    if snapshot.is_corrupted:
        add_finding(
            findings,
            title="Повреждённый файл",
            category="integrity",
            severity="error",
            expected="Документ корректно открывается",
            found="Документ повреждён или не может быть прочитан",
            location="файл",
            recommendation="Пересохраните документ в Word и загрузите заново",
        )
        return _make_result(findings, snapshot.size, cfg, None, check_errors)

    _run_check_safe("file_intake", run_file_intake_checks, snapshot, cfg, findings, check_errors)

    if snapshot.extension != ".docx":
        add_finding(
            findings,
            title="Формат не поддерживает полную проверку",
            category="file",
            severity="warning",
            expected="DOCX-файл для полноценного анализа оформления",
            found=f"Файл с расширением «{snapshot.extension}»",
            location="input",
            recommendation="Загрузите документ в формате DOCX",
        )
        return _make_result(findings, snapshot.size, cfg, None, check_errors)

    if snapshot.extension == ".docx":
        checks: list[tuple[str, CheckFunc]] = [
            ("integrity", run_integrity_checks),
            ("context_extraction", run_context_extraction_checks),
            ("work_formats", run_work_formats_checks),
            ("layout", run_layout_checks),
            ("typography", run_typography_checks),
            ("heading_formatting", run_heading_formatting_checks),
            ("heading_semantics", run_heading_semantics_checks),
            ("heading_numbering", run_heading_numbering_checks),
            ("structure", run_structure_checks),
            ("volume", run_volume_checks),
            ("bibliography", run_bibliography_checks),
            ("objects", run_objects_checks),
            ("page_numbering", run_page_numbering_checks),
            ("section_breaks", run_section_breaks_checks),
            ("toc", run_toc_checks),
            ("footnotes", run_footnotes_checks),
            ("captions", run_captions_checks),
            ("text_cleanliness", run_text_cleanliness_checks),
            ("list_formatting", run_list_formatting_checks),
        ]
        for name, func in checks:
            _run_check_safe(name, func, snapshot, cfg, findings, check_errors)

    autofix_output_path: str | None = None
    if snapshot.extension == ".docx":
        try:
            autofix = apply_safe_autofixes(
                file_path, rules, findings,
                admin_autofix_config=admin_autofix_config,
            )
            autofix_output_path = autofix.output_file_path
        except Exception:
            logger.exception("Autofix crashed for %s", file_path)
            check_errors.append("Автоисправление завершилось с внутренней ошибкой")

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

    logger.info(
        "Checks finished: %s — errors=%d, warnings=%d, internal_errors=%d",
        file_path,
        sum(1 for f in findings if f.severity == "error"),
        sum(1 for f in findings if f.severity == "warning"),
        len(check_errors),
    )
    return _make_result(findings, snapshot.size, cfg, autofix_output_path, check_errors)


def _make_result(
    findings: list[Finding],
    size: int,
    cfg: RulesConfig,
    output_path: str | None,
    check_errors: list[str] | None = None,
) -> dict:
    return {
        "summary": _summary(findings, size),
        "findings": [x.to_dict() for x in findings],
        "rules_meta": {"blocks_count": cfg.blocks_count()},
        "output_docx_path": output_path,
        "check_errors": check_errors or [],
    }
