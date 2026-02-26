from __future__ import annotations

"""
Проверки страницы и полей (layout) и базового оформления текста (typography).
"""

from backend.rules_engine.docx_utils import LoadedDocx, get_layout_margins_mm
from backend.rules_engine.findings import Finding, FindingLocation
from backend.rules_engine.schemas import TemplateRulesConfig


def run_layout_and_typography_checks(
    rules: TemplateRulesConfig,
    loaded: LoadedDocx,
) -> list[Finding]:
    findings: list[Finding] = []

    if rules.layout is not None:
        findings.extend(_check_layout(rules, loaded))

    if rules.typography is not None:
        # Сейчас проверяем только базовые параметры body, без прохода по каждому абзацу.
        findings.extend(_check_typography_config(rules))

    return findings


def _check_layout(rules: TemplateRulesConfig, loaded: LoadedDocx) -> list[Finding]:
    cfg = rules.layout
    assert cfg is not None

    findings: list[Finding] = []
    margins_actual = get_layout_margins_mm(loaded.doc)

    for side in ("top", "bottom", "left", "right"):
        expected_mm = float(cfg.margins_mm.get(side, 0))
        actual_mm = float(margins_actual.get(side, 0.0))
        diff = abs(actual_mm - expected_mm)
        if diff > cfg.tolerance_mm:
            findings.append(
                Finding(
                    rule_id=f"layout.margins.{side}",
                    title=f"Поле страницы ({side}) не соответствует шаблону",
                    category="page_layout",
                    severity="error",
                    expected=f"{expected_mm:.1f} мм (допуск {cfg.tolerance_mm} мм)",
                    actual=f"{actual_mm:.1f} мм",
                    recommendation="Измените поля страницы в настройках Word согласно требованиям вуза.",
                    location=FindingLocation(),
                )
            )

    return findings


def _check_typography_config(rules: TemplateRulesConfig) -> list[Finding]:
    """
    Минимальная проверка: наличие и корректность базовых параметров.

    Полноценная проверка каждого абзаца будет добавлена отдельным шагом,
    сейчас важно, чтобы движок уже формировал findings по этому блоку.
    """
    cfg = rules.typography
    assert cfg is not None

    findings: list[Finding] = []

    # Пример: если кегль или шрифт не заданы, считаем это ошибкой конфигурации шаблона.
    if not cfg.body.font or cfg.body.size_pt <= 0:
        findings.append(
            Finding(
                rule_id="typography.body.config",
                title="Не заданы параметры основного текста",
                category="typography",
                severity="error",
                expected="В шаблоне должны быть заданы шрифт и размер основного текста.",
                actual="Параметры шрифта/размера для основного текста неполные.",
                recommendation="Администратору: дополните шаблон правилами оформления основного текста.",
                location=FindingLocation(),
            )
        )

    return findings



