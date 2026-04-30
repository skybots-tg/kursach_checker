from __future__ import annotations

from pydantic import BaseModel, Field


class DocConverterSettings(BaseModel):
    """Настройки конвертера DOC→DOCX."""

    enabled: bool = False
    command_template: str = Field(
        "",
        description='Command template, e.g.: soffice --headless --convert-to "docx:Office Open XML Text" --outdir "{outdir}" "{input}"',
    )
    timeout_sec: int = Field(60, ge=5, le=600)


class DocConverterTestResult(BaseModel):
    ok: bool
    message: str
    converter_version: str | None = None


class WelcomeBonusSettings(BaseModel):
    """Приветственный бонус новым пользователям при первом /start."""

    amount: int = Field(
        3,
        ge=0,
        le=1000,
        description=(
            "Сколько бесплатных проверок получает новый пользователь. "
            "0 — бонус выключен."
        ),
    )


class SystemSettingsOut(BaseModel):
    doc_converter: DocConverterSettings = Field(default_factory=DocConverterSettings)
    welcome_bonus: WelcomeBonusSettings = Field(default_factory=WelcomeBonusSettings)


class SettingValueOut(BaseModel):
    key: str
    value: dict
