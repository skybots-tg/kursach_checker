from __future__ import annotations

from dataclasses import dataclass

_ALIGN_DISPLAY: dict[str, str] = {
    "LEFT": "\u041f\u043e \u043b\u0435\u0432\u043e\u043c\u0443 \u043a\u0440\u0430\u044e",
    "CENTER": "\u041f\u043e \u0446\u0435\u043d\u0442\u0440\u0443",
    "RIGHT": "\u041f\u043e \u043f\u0440\u0430\u0432\u043e\u043c\u0443 \u043a\u0440\u0430\u044e",
    "JUSTIFY": "\u041f\u043e \u0448\u0438\u0440\u0438\u043d\u0435",
    "DISTRIBUTE": "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0451\u043d\u043d\u043e\u0435",
}


def display_alignment(raw: str | None, *, inherited: bool = False) -> str:
    if raw is None:
        label = _ALIGN_DISPLAY["LEFT"]
        return f"{label} (\u0443\u043d\u0430\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u043e)" if inherited else label
    upper = raw.upper()
    for key, label in _ALIGN_DISPLAY.items():
        if key in upper:
            return label
    return raw


@dataclass(slots=True)
class Finding:
    title: str
    category: str
    severity: str
    expected: str
    found: str
    location: str
    recommendation: str
    auto_fixed: bool = False
    auto_fix_details: str | None = None

    def to_dict(self) -> dict:
        payload = {
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "expected": self.expected,
            "found": self.found,
            "location": self.location,
            "recommendation": self.recommendation,
            "auto_fixed": self.auto_fixed,
        }
        if self.auto_fix_details:
            payload["auto_fix_details"] = self.auto_fix_details
        return payload


def add_finding(
    findings: list[Finding],
    *,
    title: str,
    category: str,
    severity: str,
    expected: str,
    found: str,
    location: str,
    recommendation: str,
    auto_fixed: bool = False,
    auto_fix_details: str | None = None,
) -> None:
    if severity == "off":
        return
    findings.append(
        Finding(
            title=title,
            category=category,
            severity=severity,
            expected=expected,
            found=found,
            location=location,
            recommendation=recommendation,
            auto_fixed=auto_fixed,
            auto_fix_details=auto_fix_details,
        )
    )


