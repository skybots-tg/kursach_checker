from __future__ import annotations

from dataclasses import dataclass


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

