"""Quick diagnostic: run rules engine on the kolytsheva draft."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from run_test_checks import GOST_RULES  # noqa: E402
from app.rules_engine.runner import run_document_checks  # noqa: E402
from app.rules_engine.autofix import apply_safe_autofixes  # noqa: E402


async def main() -> None:
    src = BASE / "tmp_check.docx"
    print(f"Source: {src}, exists={src.exists()}, size={src.stat().st_size}")

    print("\n=== run_document_checks ===")
    try:
        report = await run_document_checks(str(src), GOST_RULES)
    except Exception:
        traceback.print_exc()
        return

    summary = report["summary"]
    print(f"summary: {summary}")
    print(f"output_docx_path: {report.get('output_docx_path')}")
    print(f"check_errors: {report.get('check_errors')}")

    print("\n=== findings ===")
    for f in report["findings"]:
        sev = f["severity"]
        fixed = " [FIXED]" if f.get("auto_fixed") else ""
        print(f"  [{sev.upper()}]{fixed} {f['title']} :: {f['location']}")
        print(f"     expected: {f['expected'][:160]}")
        print(f"     found:    {f['found'][:160]}")
        if f.get("auto_fix_details"):
            print(f"     details:  {f['auto_fix_details'][:300]}")

    out = BASE / "tmp_check.report.json"
    with out.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"\nreport saved to {out}")

    print("\n=== direct apply_safe_autofixes ===")
    try:
        findings: list = []
        result = apply_safe_autofixes(str(src), GOST_RULES, findings)
        print(f"output_file_path: {result.output_file_path}")
        print(f"details count: {len(result.details)}")
        for d in result.details[:30]:
            print(f"  - {d}")
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
