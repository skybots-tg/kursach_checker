from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)


BOT_TOKEN = os.getenv("BOT_TOKEN", "CHANGE_ME_BOT_TOKEN")
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://example.com/miniapp")


def build_main_keyboard() -> InlineKeyboardMarkup:
    """
    Главное inline‑меню бота.

    Mini App переиспользуется с разными вкладками через query‑параметр tab.
    Конкретная реализация вкладок — на стороне фронтенда Mini App.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Проверить документ",
                    web_app=WebAppInfo(url=MINIAPP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Мои проверки",
                    web_app=WebAppInfo(url=f"{MINIAPP_URL}?tab=history"),
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ О сервисе",
                    callback_data="menu:about",
                ),
                InlineKeyboardButton(
                    text="💬 Поддержка",
                    callback_data="menu:support",
                ),
            ],
        ]
    )


async def cmd_start(message: Message) -> None:
    """
    Стартовое сообщение бота c основным меню и кнопкой открытия Mini App.
    """
    await message.answer(
        "👋 Добро пожаловать в систему технической проверки курсовых и ВКР.\n\n"
        "Через этот бот вы можете оплатить проверку, загрузить документ и получить отчёт "
        "по оформлению по правилам вуза и ГОСТ.",
        reply_markup=build_main_keyboard(),
    )


async def on_menu_callback(callback: CallbackQuery) -> None:
    """
    Обработчик простых пунктов меню (О сервисе, Поддержка).

    На MVP этапе тексты заданы в коде. В дальнейшем можно вынести их в bot_content
    и подгружать из backend‑сервиса.
    """
    data = callback.data or ""
    if data == "menu:about":
        text = (
            "📌 <b>О сервисе</b>\n\n"
            "Сервис автоматически проверяет техническое оформление документа "
            "(поля, шрифт, интервалы, структуру разделов, список источников и т.д.) "
            "по правилам вуза и ГОСТ.\n\n"
            "Смысл текста не оценивается — только форматирование и структура."
        )
    elif data == "menu:support":
        text = (
            "💬 <b>Поддержка</b>\n\n"
            "Если что‑то пошло не так, напишите в поддержку: @your_support_username.\n"
            "Пожалуйста, приложите скриншоты и описание проблемы."
        )
    else:
        await callback.answer()
        return

    await callback.message.edit_reply_markup(reply_markup=build_main_keyboard())
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.callback_query.register(on_menu_callback, F.data.startswith("menu:"))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())




