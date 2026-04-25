"""Run autofix on test documents and analyze the results."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.rules_engine.autofix import apply_safe_autofixes
from app.rules_engine.findings import Finding

GOST_RULES = {
    "blocks": [
        {
            "key": "autofix",
            "title": "Автоисправления",
            "enabled": True,
            "severity": "advice",
            "params": {
                "normalize_alignment": True,
                "normalize_line_spacing": True,
                "normalize_first_line_indent": True,
                "normalize_spacing_before_after": True,
                "normalize_font": True,
                "normalize_margins": True,
                "normalize_headings": True,
                "space_before_pt": 0,
                "space_after_pt": 0,
                "generate_toc": True,
                "normalize_toc_heading": True,
                "fix_bibliography": True,
                "normalize_dashes": True,
                "remove_highlight": True,
                "remove_strange_chars": True,
                "strip_leading_whitespace": True,
                "fix_section_breaks": True,
                "normalize_font_color": True,
                "normalize_list_markers": True,
                "normalize_body_left_indent": True,
                "collapse_empty_paras": True,
                "max_consecutive_empty_paras": 1,
                "promote_heading_candidates": True,
            },
        },
    ]
}

ADMIN_CFG = {
    "defaults": {},
    "safety_limits": {
        "max_paragraphs_touched": 5000,
        "skip_toc": True,
        "skip_headings": False,
        "allow_promote_heading_candidates": True,
        "skip_tables": False,
        "skip_margin_normalization": False,
        "libreoffice_toc_refresh": False,
    },
}


def run_test(doc_path: str, label: str):
    import io, sys
    out = io.open(f"test_docs/{label}.log", "w", encoding="utf-8")
    out.write(f"\n{'='*60}\n")
    out.write(f"  {label}: {doc_path}\n")
    out.write(f"{'='*60}\n")
    findings: list[Finding] = []
    result = apply_safe_autofixes(
        doc_path, GOST_RULES, findings, admin_autofix_config=ADMIN_CFG,
    )
    out.write(f"  Output: {result.output_file_path}\n")
    out.write(f"  Details ({len(result.details)}):\n")
    for d in result.details:
        out.write(f"    - {d}\n")
    out.close()
    print(f"  {label}: {len(result.details)} details -> {label}.log")
    return result


if __name__ == "__main__":
    test_dir = Path(__file__).parent

    r1 = run_test(str(test_dir / "referat_4.docx"), "Реферат 4")
    r2 = run_test(str(test_dir / "referat_meo.docx"), "Реферат МЭО")

    # Now analyze the fixed docs
    if r1.output_file_path:
        from test_docs.analyze_issues import analyze
        data = analyze(r1.output_file_path)
        out_path = test_dir / "referat4_fixed_analysis.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n  Fixed analysis saved to {out_path}")

    if r2.output_file_path:
        from test_docs.analyze_issues import analyze
        data = analyze(r2.output_file_path)
        out_path = test_dir / "referat_meo_fixed_analysis.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n  Fixed analysis saved to {out_path}")
