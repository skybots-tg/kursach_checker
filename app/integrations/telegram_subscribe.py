"""Логика проверки подписки на канал в боте.

Вынесено из ``telegram_bot.py`` ради ограничения 500 строк на файл.
Здесь живут:
* сборка inline-клавиатур пункта «получи бонус за подписку» и
  кнопки повторной проверки,
* обработчик callback'а «✅ Проверить подписку» (нажимая её,
  пользователь запускает getChatMember и при первом успехе получает
  начисление кредитов).

Сообщения пользователю шлются с трекингом через коллбэк ``track``,
который ``telegram_bot`` передаёт сюда (нужен, чтобы при следующем
переходе бот мог удалить эти сообщения).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Awaitable

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.db.session import SessionLocal
from app.integrations.telegram_constants import SUBSCRIBE_CHECK_CB
from app.models import CreditsBalance, User
from app.services import subscribe_bonus
from app.services.bot_texts import get_text
from app.services.subscribe_bonus import SubscribeOutcome


# Коллбэк для трекинга bot-сообщений (чтобы их можно было удалить позже).
TrackFn = Callable[[int, int], Awaitable[None] | None]


async def build_subscribe_menu_keyboard() -> InlineKeyboardMarkup | None:
    """Клавиатура пункта меню «получи бонус за подписку».

    Две кнопки: «Перейти в канал» (URL) и «Проверить подписку» (callback).
    Возвращает ``None``, если фича выключена в env — тогда у пункта не
    будет ни ссылки, ни проверки.
    """
    if not subscribe_bonus.is_enabled():
        return None

    btn_open = await get_text("subscribe.btn_open")
    btn_check = await get_text("subscribe.btn_check")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=btn_open, url=subscribe_bonus.channel_link(),
            )],
            [InlineKeyboardButton(
                text=btn_check, callback_data=SUBSCRIBE_CHECK_CB,
            )],
        ],
    )


async def build_subscribe_retry_keyboard() -> InlineKeyboardMarkup:
    """Кнопка повторной проверки подписки.

    Используется и под маркером ``{subscribe_btn}`` в произвольных пунктах
    меню, и в ответе «не вижу подписки» — чтобы пользователь мог нажать
    ещё раз без возврата в меню.
    """
    btn_check = await get_text("subscribe.btn_check")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=btn_check, callback_data=SUBSCRIBE_CHECK_CB,
            )],
        ],
    )


async def handle_subscribe_check(
    bot: Bot, *, chat_id: int, tg_user_id: int, track: TrackFn,
) -> None:
    """Обработчик нажатия «Проверить подписку».

    Проверяет подписку через ``getChatMember``, при первом успехе
    начисляет ``SUBSCRIBE_BONUS_AMOUNT`` кредитов и шлёт пользователю
    сообщение с результатом. Старое сообщение с кнопками не трогаем —
    пусть остаётся, чтобы можно было перепроверить.
    """
    if not subscribe_bonus.is_enabled():
        text = await get_text("subscribe.disabled")
        sent = await bot.send_message(chat_id, text)
        await _track(track, chat_id, sent.message_id)
        return

    outcome = SubscribeOutcome.error
    new_balance = 0

    async with SessionLocal() as db:
        user = await db.scalar(
            select(User).where(User.telegram_id == tg_user_id)
        )
        if user is None:
            text = await get_text("check.need_start")
            sent = await bot.send_message(chat_id, text)
            await _track(track, chat_id, sent.message_id)
            return

        outcome = await subscribe_bonus.try_grant_subscribe_bonus(
            db, bot, user_id=user.id, telegram_user_id=tg_user_id,
        )

        if outcome is SubscribeOutcome.granted:
            balance = await db.get(CreditsBalance, user.id)
            if balance is not None:
                new_balance = balance.credits_available
            await db.commit()

    text, parse_mode, retry_kb = await _format_outcome(outcome, new_balance)
    sent = await bot.send_message(
        chat_id, text, parse_mode=parse_mode, reply_markup=retry_kb,
    )
    await _track(track, chat_id, sent.message_id)


async def _format_outcome(
    outcome: SubscribeOutcome, new_balance: int,
) -> tuple[str, str | None, InlineKeyboardMarkup | None]:
    """Подобрать текст ответа, parse_mode и клавиатуру по результату."""
    if outcome is SubscribeOutcome.granted:
        text = await get_text(
            "subscribe.granted",
            bonus=subscribe_bonus.bonus_amount(),
            credits=new_balance,
        )
        return text, "HTML", None

    if outcome is SubscribeOutcome.already_received:
        text = await get_text("subscribe.already")
        return text, "HTML", None

    if outcome is SubscribeOutcome.not_subscribed:
        text = await get_text(
            "subscribe.not_subscribed",
            bonus=subscribe_bonus.bonus_amount(),
        )
        return text, None, await build_subscribe_retry_keyboard()

    if outcome is SubscribeOutcome.disabled:
        text = await get_text("subscribe.disabled")
        return text, None, None

    text = await get_text("subscribe.error")
    return text, None, await build_subscribe_retry_keyboard()


async def _track(track: TrackFn, chat_id: int, message_id: int) -> None:
    """Совместимо вызвать track-функцию (sync или async)."""
    result = track(chat_id, message_id)
    if hasattr(result, "__await__"):
        await result
