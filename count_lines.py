files = [
    "app/rules_engine/autofix.py",
    "app/rules_engine/autofix_helpers.py",
    "app/rules_engine/checks_advanced.py",
    "app/rules_engine/template_schema.py",
]
for f in files:
    with open(f, encoding="utf-8") as fh:
        lines = sum(1 for _ in fh)
    status = "OK" if lines <= 500 else "OVER LIMIT"
    print(f"{f}: {lines} lines [{status}]")
