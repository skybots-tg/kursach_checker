from __future__ import annotations

from pathlib import Path

from app.rules_engine.runner import run_document_checks
from app.services.doc_conversion import convert_doc_to_docx, get_converter_settings_from_db


def resolve_doc_policy(rules: dict | None) -> str:
    blocks = (rules or {}).get("blocks", []) if isinstance(rules, dict) else []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("key") != "file_intake":
            continue
        params = block.get("params") or {}
        policy = str(params.get("doc_policy", "allow")).lower()
        if policy in {"reject", "allow", "convert"}:
            return policy
    return "allow"


async def run_check_pipeline(input_path: str, rules: dict | None) -> dict:
    source = Path(input_path)
    working_path = str(source)
    notices: list[str] = []

    if source.suffix.lower() == ".doc":
        policy = resolve_doc_policy(rules)
        if policy == "reject":
            return _error_result("DOC-файлы запрещены политикой шаблона. Загрузите DOCX", notices)
        if policy == "convert":
            cmd, timeout, enabled = await get_converter_settings_from_db()
            if not enabled or not cmd:
                return _error_result("DOC-конвертация отключена или не настроена администратором", notices)
            converted_path, err = convert_doc_to_docx(
                str(source), command_template=cmd, timeout_sec=timeout,
            )
            if err:
                return _error_result(err, notices)
            if converted_path:
                working_path = converted_path
                notices.append("DOC конвертирован в DOCX согласно политике шаблона")

    report = await run_document_checks(working_path, rules)
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


