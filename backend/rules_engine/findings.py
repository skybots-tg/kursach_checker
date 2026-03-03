from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["error", "warning", "info"]
Category = Literal[
    "file",
    "integrity",
    "page_layout",
    "typography",
    "structure",
    "bibliography",
    "volume",
    "objects",
]


class FindingLocation(BaseModel):
    section_id: str | None = None
    section_title: str | None = None
    page: int | None = None
    paragraph_index: int | None = None


class Finding(BaseModel):
    """
    Элемент отчёта, который потом напрямую отображается в Mini App / админке.
    """

    rule_id: str
    title: str
    category: Category
    severity: Severity
    expected: str
    actual: str
    recommendation: str
    location: FindingLocation | None = None
    auto_fixed: bool = False
    auto_fix_description: str | None = None


class CheckReport(BaseModel):
    """
    Полный отчёт проверки, который сохраняется как JSON и используется и для демо, и для реальных проверок.
    """

    template_profile_id: str
    template_version_id: int
    summary_errors: int
    summary_warnings: int
    summary_autofixed: int
    findings: list[Finding] = Field(default_factory=list)






