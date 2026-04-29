"""Реестр «дополнительных» inline-кнопок пункта меню.

Админ в форме редактирования пункта меню включает нужные галочки —
бот при отправке этого пункта добавит соответствующие кнопки под
обычной клавиатурой. Каждая кнопка описана здесь декларативно:

* ``code``      — стабильный идентификатор, попадает в ``ContentMenuItem.extra_buttons``;
* ``label_ru``  — подпись для админки (свитч);
* ``hint_ru``   — короткое объяснение;
* ``available`` — функция, проверяющая что фича вообще включена
                  (например, есть env-настройка), иначе кнопку можно
                  не показывать админу.

Сама сборка inline-кнопки выполняется в ``build_extra_buttons``: на
каждый код возвращается ``InlineKeyboardButton`` или ``None`` (если
кнопку нельзя построить, например, не задан HTTPS-URL).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aiogram.types import InlineKeyboardButton, WebAppInfo

from app.core.config import settings
from app.integrations.telegram_constants import (
    REFERRAL_PAYLOAD,
    SUBSCRIBE_BONUS_PAYLOAD,
    SUBSCRIBE_CHECK_CB,
)
from app.services import subscribe_bonus
from app.services.bot_texts import get_text


# ---------------------------------------------------------------------------
#  Доступные коды и их подписи (для админки и для бота)
# ---------------------------------------------------------------------------

def _subscribe_check_available() -> bool:
    return subscribe_bonus.is_enabled() and subscribe_bonus.bonus_amount() > 0


def _pay_available() -> bool:
    base = (settings.app_base_url or "").strip().rstrip("/")
    return bool(
        base
        and base != "https://example.com"
        and base.startswith("https://")
    )


def _referral_available() -> bool:
    return True


def _subscribe_open_available() -> bool:
    return subscribe_bonus.is_enabled()


EXTRA_BUTTON_CODES: list[dict[str, Any]] = [
    {
        "code": "subscribe_check",
        "label_ru": "Проверить подписку",
        "hint_ru": (
            "Добавит inline-кнопку, по которой бот проверит подписку "
            "пользователя на канал и при первом успехе начислит бонус."
        ),
        "available": _subscribe_check_available,
    },
    {
        "code": "subscribe_open",
        "label_ru": "Перейти в канал",
        "hint_ru": "Inline-кнопка-ссылка на канал из настройки SUBSCRIBE_BONUS_CHANNEL_USERNAME.",
        "available": _subscribe_open_available,
    },
    {
        "code": "pay",
        "label_ru": "Оплатить (открыть Mini App)",
        "hint_ru": (
            "WebApp-кнопка открытия Mini App по APP_BASE_URL. "
            "Появится только если URL начинается с https://."
        ),
        "available": _pay_available,
    },
    {
        "code": "referral",
        "label_ru": "Пригласить друга",
        "hint_ru": "Переход в раздел реферальной программы (с твоей реф-ссылкой).",
        "available": _referral_available,
    },
]

EXTRA_BUTTON_CODE_SET: set[str] = {b["code"] for b in EXTRA_BUTTON_CODES}


def list_extra_button_meta() -> list[dict[str, Any]]:
    """Метаданные кнопок для админки (что показать, что доступно)."""
    return [
        {
            "code": b["code"],
            "label": b["label_ru"],
            "hint": b["hint_ru"],
            "available": b["available"](),
        }
        for b in EXTRA_BUTTON_CODES
    ]


def normalize_extra_buttons(value: Any) -> list[str]:
    """Привести значение из API к чистому списку известных кодов.

    Тихо отбрасываем неизвестные коды — старые миграции/БД могут
    хранить мусор, валиться на этом не хочется.
    """
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        if item in EXTRA_BUTTON_CODE_SET and item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
#  Сборка inline-кнопок
# ---------------------------------------------------------------------------

async def _btn_subscribe_check() -> InlineKeyboardButton | None:
    if not _subscribe_check_available():
        return None
    label = await get_text("subscribe.btn_check")
    return InlineKeyboardButton(text=label, callback_data=SUBSCRIBE_CHECK_CB)


async def _btn_subscribe_open() -> InlineKeyboardButton | None:
    if not _subscribe_open_available():
        return None
    label = await get_text("subscribe.btn_open")
    return InlineKeyboardButton(text=label, url=subscribe_bonus.channel_link())


async def _btn_pay() -> InlineKeyboardButton | None:
    if not _pay_available():
        return None
    label = await get_text("check.no_credits_btn_pay")
    base = (settings.app_base_url or "").strip().rstrip("/")
    return InlineKeyboardButton(text=label, web_app=WebAppInfo(url=base))


async def _btn_referral() -> InlineKeyboardButton | None:
    label = await get_text("check.no_credits_btn_referral")
    return InlineKeyboardButton(text=label, callback_data=REFERRAL_PAYLOAD)


_BTN_BUILDERS: dict[str, Callable[[], Any]] = {
    "subscribe_check": _btn_subscribe_check,
    "subscribe_open": _btn_subscribe_open,
    "pay": _btn_pay,
    "referral": _btn_referral,
}


async def build_extra_buttons(
    codes: list[str],
) -> list[list[InlineKeyboardButton]]:
    """Собрать inline-ряды по списку кодов (по одной кнопке в ряду)."""
    rows: list[list[InlineKeyboardButton]] = []
    for code in normalize_extra_buttons(codes):
        builder = _BTN_BUILDERS.get(code)
        if builder is None:
            continue
        btn = await builder()
        if btn is not None:
            rows.append([btn])
    return rows
