from __future__ import annotations

from pydantic import BaseModel, Field


class DocConverterSettings(BaseModel):
    """Настройки конвертера DOC→DOCX."""

    enabled: bool = False
    command_template: str = Field(
        "",
        description='Шаблон команды, например: soffice --headless --convert-to docx --outdir "{outdir}" "{input}"',
    )
    timeout_sec: int = Field(60, ge=5, le=600)


class DocConverterTestResult(BaseModel):
    ok: bool
    message: str
    converter_version: str | None = None


class SystemSettingsOut(BaseModel):
    doc_converter: DocConverterSettings = Field(default_factory=DocConverterSettings)


class SettingValueOut(BaseModel):
    key: str
    value: dict
