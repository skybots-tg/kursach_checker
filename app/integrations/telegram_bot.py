from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.core.config import settings


def build_main_keyboard() -> InlineKeyboardMarkup:
    mini_app_url = "https://example.com/mini-app"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Проверить документ", web_app=WebAppInfo(url=mini_app_url))],
            [InlineKeyboardButton(text="Мои проверки", web_app=WebAppInfo(url=f"{mini_app_url}#/history"))],
            [InlineKeyboardButton(text="FAQ", callback_data="faq")],
        ]
    )


async def run_bot() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        await message.answer(
            "Добро пожаловать в сервис технической проверки документов.",
            reply_markup=build_main_keyboard(),
        )

    await dp.start_polling(bot)


