from __future__ import annotations

import logging
from pathlib import Path

from app.rules_engine.runner import run_document_checks
from app.services.doc_conversion import convert_doc_to_docx, get_converter_settings_from_db

logger = logging.getLogger(__name__)


def resolve_doc_policy(rules: dict | None) -> str:
    blocks = (rules or {}).get("blocks", []) if isinstance(rules, dict) else []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("key") != "file_intake":
            continue
        params = block.get("params") or {}
        policy = str(params.get("doc_policy", "convert")).lower()
        if policy in {"reject", "convert"}:
            return policy
    return "convert"


async def run_check_pipeline(input_path: str, rules: dict | None) -> dict:
    logger.info("Pipeline started: %s", input_path)
    source = Path(input_path)
    working_path = str(source)
    notices: list[str] = []

    if not source.exists():
        logger.error("Input file does not exist: %s", input_path)
        return _error_result("Входной файл не найден на диске", notices)

    if source.suffix.lower() == ".doc":
        policy = resolve_doc_policy(rules)
        logger.info("DOC file detected, policy=%s", policy)
        if policy == "reject":
            return _error_result("DOC-файлы запрещены политикой шаблона. Загрузите DOCX", notices)
        if policy == "convert":
            try:
                cmd, timeout, enabled = await get_converter_settings_from_db()
            except Exception:
                logger.exception("Failed to get converter settings from DB")
                return _error_result("Ошибка получения настроек конвертера из БД", notices)
            if not enabled or not cmd:
                return _error_result("DOC-конвертация отключена или не настроена администратором", notices)
            converted_path, err = convert_doc_to_docx(
                str(source), command_template=cmd, timeout_sec=timeout,
            )
            if err:
                logger.warning("DOC conversion failed: %s", err)
                return _error_result(err, notices)
            if converted_path:
                working_path = converted_path
                notices.append(
                    "DOC converted to DOCX; "
                    "check results may differ from the original document"
                )
                logger.info("DOC converted to DOCX: %s", converted_path)

    try:
        report = await run_document_checks(working_path, rules)
    except Exception:
        logger.exception("run_document_checks crashed for %s", working_path)
        return _error_result("Внутренняя ошибка при проверке документа", notices)

    logger.info(
        "Pipeline finished: %s — errors=%d, warnings=%d",
        input_path,
        report.get("summary", {}).get("errors", 0),
        report.get("summary", {}).get("warnings", 0),
    )

    return {
        "ok": True,
        "error": None,
        "report": report,
        "output_docx_path": report.get("output_docx_path"),
        "source_docx_path": working_path if working_path.lower().endswith(".docx") else None,
        "pipeline_notices": notices,
    }


def _error_result(error: str, notices: list[str]) -> dict:
    return {
        "ok": False,
        "error": error,
        "report": None,
        "output_docx_path": None,
        "source_docx_path": None,
        "pipeline_notices": notices,
    }


