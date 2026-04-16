"""Configurable bot texts with DB override and fallback defaults.

Every text the bot sends to users is defined here with a machine key,
human-readable label, description and default value.  Admin can override
any text via the ``bot_content`` table (same table used by the existing
content-texts feature).  Texts support ``{variable}`` placeholders that
are substituted at runtime.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models import BotContent

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
#  Registry of system texts
# ------------------------------------------------------------------

SYSTEM_TEXTS: dict[str, dict[str, Any]] = {
    "bot.welcome": {
        "label": "Приветственное сообщение",
        "group": "Общие",
        "description": "Отправляется при /start и переходе в главное меню",
        "default": (
            "Хочешь работу, которую примут с первого раза — без правок и переделок? <b>🔥</b>\n"
            "\n"
            "Я Анастасия Ахметова, основатель академии помощи студентам.\n"
            "\n"
            "С 2013 года мы помогли более чем <b>90 000 студентам</b>, и сейчас в команде уже <b>450+ авторов</b> по всем специальностям.\n"
            "\n"
            "<blockquote>Поэтому я создала этот бот как твой спасательный круг. \n"
            "Здесь можно и оформить любую работу по ГОСТу, и заказать любую учебную работу 🚀</blockquote>\n"
            "<b>\n"
            "Выбирай нужный раздел в меню и начинаем 👇🏼</b>"
        ),
        "supports_html": True,
        "variables": [],
    },

    # -- Document handling --
    "check.only_doc_docx": {
        "label": "Неподдерживаемый формат файла",
        "group": "Проверка документа",
        "description": "Когда пользователь отправляет файл не в формате DOC/DOCX",
        "default": "Я принимаю только файлы в формате DOC и DOCX. Пожалуйста, отправьте документ в одном из этих форматов.",
        "supports_html": False,
        "variables": [],
    },
    "check.file_too_big": {
        "label": "Файл слишком большой",
        "group": "Проверка документа",
        "description": "Когда размер файла превышает лимит",
        "default": "Файл слишком большой 😔\nМаксимальный размер — {max_mb} МБ.",
        "supports_html": False,
        "variables": ["max_mb"],
    },
    "check.need_start": {
        "label": "Пользователь не зарегистрирован",
        "group": "Проверка документа",
        "description": "Когда пользователь отправляет файл до команды /start",
        "default": "Для начала работы нажмите /start — это займёт пару секунд!",
        "supports_html": False,
        "variables": [],
    },
    "check.no_credits": {
        "label": "Недостаточно кредитов",
        "group": "Проверка документа",
        "description": "Когда у пользователя закончились проверки",
        "default": (
            "<b>Ты выжал из бота все 3 бесплатные проверки 🥺</b>\n"
            "\n"
            "дальше можно идти без паузы: <b>по 50₽ за оформленную работу</b>.\n"
            "\n"
            "<blockquote><b>выбирай, как удобнее:</b>\n"
            "➡️ оплатить и сразу продолжить;\n"
            "➡️ написать менеджеру, если нужна не только проверка оформления, но и помощь с самой работой</blockquote>\n"
            "@kursach_d"
        ),
        "supports_html": True,
        "variables": [],
    },
    "check.upload_prompt": {
        "label": "Приглашение загрузить файл (со счётчиком)",
        "group": "Проверка документа",
        "description": "Показывается после кнопки «Отправить новый файл». Переменная: {credits}",
        "default": (
            "(у тебя осталось {credits} попыток)\n"
            "\n"
            "<b>Загрузи свой файл:📝</b>"
        ),
        "supports_html": True,
        "variables": ["credits"],
    },
    "check.no_templates": {
        "label": "Нет активных шаблонов",
        "group": "Проверка документа",
        "description": "Когда в системе нет ни одного активного шаблона проверки",
        "default": "Сейчас проверка недоступна — нет настроенных шаблонов. Попробуйте позже или обратитесь в поддержку.",
        "supports_html": False,
        "variables": [],
    },
    "check.downloading": {
        "label": "Скачивание файла",
        "group": "Проверка документа",
        "description": "Статусное сообщение при скачивании файла",
        "default": "⏳ Скачиваю ваш файл…",
        "supports_html": False,
        "variables": [],
    },
    "check.download_failed": {
        "label": "Ошибка скачивания",
        "group": "Проверка документа",
        "description": "Когда не удалось скачать файл из Telegram",
        "default": "Не удалось скачать файл 😔\nПопробуйте отправить его ещё раз.",
        "supports_html": False,
        "variables": [],
    },
    "check.processing": {
        "label": "Идёт проверка",
        "group": "Проверка документа",
        "description": "Статусное сообщение во время проверки документа",
        "default": "🔍 Проверяю ваш документ — это займёт несколько секунд…",
        "supports_html": False,
        "variables": [],
    },
    "check.queued": {
        "label": "Документ принят в очередь",
        "group": "Проверка документа",
        "description": "Когда документ поставлен в очередь на проверку",
        "default": "✅ Ваш документ принят в обработку!\nМы пришлём результат, как только проверка завершится.",
        "supports_html": False,
        "variables": [],
    },
    "check.error": {
        "label": "Ошибка проверки",
        "group": "Проверка документа",
        "description": "Когда проверка завершилась с ошибкой",
        "default": "Произошла ошибка при проверке 😔\nПопробуйте ещё раз через пару минут.",
        "supports_html": False,
        "variables": [],
    },
    "check.error_detail": {
        "label": "Ошибка проверки (с деталями)",
        "group": "Проверка документа",
        "description": "Когда проверка вернула конкретную ошибку",
        "default": "К сожалению, проверка не удалась: {error}",
        "supports_html": False,
        "variables": ["error"],
    },
    "check.fixed_doc_caption": {
        "label": "Подпись к исправленному документу",
        "group": "Проверка документа",
        "description": "Подпись к файлу с автоисправлениями",
        "default": "📄 Исправленный документ",
        "supports_html": False,
        "variables": [],
    },

    # -- Notification --
    "notify.check_done": {
        "label": "Уведомление о завершении проверки",
        "group": "Уведомления",
        "description": "Отправляется после завершения проверки через воркер (финальное сообщение с кнопками)",
        "default": (
            "<b>Готово ✅</b>\n"
            "\n"
            "работа уже сделана!\n"
            "\n"
            "<b>загляни в результат и проверь</b>, все ли по оформлению получилось так, как тебе нужно 👇🏼"
        ),
        "supports_html": True,
        "variables": ["check_id"],
    },
    "notify.check_done_btn_menu": {
        "label": "Кнопка «Меню» (после проверки)",
        "group": "Уведомления",
        "description": "Текст кнопки возврата в главное меню после проверки",
        "default": "🏠 Меню",
        "supports_html": False,
        "variables": [],
    },
    "notify.check_done_btn_new_file": {
        "label": "Кнопка «Отправить новый файл» (после проверки)",
        "group": "Уведомления",
        "description": "Текст кнопки для загрузки следующего файла",
        "default": "📝 Отправить новый файл",
        "supports_html": False,
        "variables": [],
    },
    "notify.check_done_btn_order": {
        "label": "Кнопка «Заказать полноценную работу» (после проверки)",
        "group": "Уведомления",
        "description": "Текст кнопки для перехода к оформлению полноценной работы",
        "default": "💎 Заказать полноценную работу",
        "supports_html": False,
        "variables": [],
    },
    "notify.check_error": {
        "label": "Уведомление об ошибке проверки",
        "group": "Уведомления",
        "description": "Отправляется, если проверка завершилась с ошибкой",
        "default": "😔 К сожалению, при проверке произошла ошибка.\nПопробуйте отправить документ ещё раз.",
        "supports_html": False,
        "variables": ["check_id"],
    },

    # -- Report formatting --
    "report.title": {
        "label": "Заголовок отчёта",
        "group": "Отчёт",
        "description": "Заголовок сообщения с результатами проверки",
        "default": "📋 <b>Результат проверки</b>",
        "supports_html": True,
        "variables": [],
    },
    "report.no_issues": {
        "label": "Нет замечаний",
        "group": "Отчёт",
        "description": "Когда документ прошёл проверку без замечаний",
        "default": "✅ Отлично! Нарушений не обнаружено — ваш документ оформлен правильно.",
        "supports_html": False,
        "variables": [],
    },
    "report.summary": {
        "label": "Сводка по замечаниям",
        "group": "Отчёт",
        "description": "Краткая сводка: ошибки, предупреждения, автоисправления. Переменные: {errors}, {warnings}, {fixed}",
        "default": "❌ Ошибок: {errors}\n⚠️ Предупреждений: {warnings}\n🔧 Автоисправлений: {fixed}",
        "supports_html": False,
        "variables": ["errors", "warnings", "fixed"],
    },
    "report.findings_header": {
        "label": "Заголовок списка замечаний",
        "group": "Отчёт",
        "description": "Перед списком конкретных замечаний",
        "default": "<b>Замечания:</b>",
        "supports_html": True,
        "variables": [],
    },
    "report.more_findings": {
        "label": "Ещё замечания",
        "group": "Отчёт",
        "description": "Когда замечаний больше, чем помещается в сообщение",
        "default": "… и ещё {count} замечаний — подробнее в приложении",
        "supports_html": False,
        "variables": ["count"],
    },
    "report.all_fixed": {
        "label": "Все замечания исправлены автоматически",
        "group": "Отчёт",
        "description": "Когда все найденные замечания были автоматически исправлены",
        "default": "✅ Все замечания исправлены автоматически ({fixed} шт.).\nСкачайте исправленный документ ниже.",
        "supports_html": False,
        "variables": ["fixed"],
    },
    "report.fixed_header": {
        "label": "Заголовок списка автоисправлений",
        "group": "Отчёт",
        "description": "Перед списком автоматически исправленных замечаний",
        "default": "<b>Исправлено автоматически:</b>",
        "supports_html": True,
        "variables": [],
    },
}


# ------------------------------------------------------------------
#  Public API
# ------------------------------------------------------------------

def get_default(key: str) -> str:
    """Return the built-in default for *key*."""
    entry = SYSTEM_TEXTS.get(key)
    if not entry:
        raise KeyError(f"Unknown system text key: {key}")
    return entry["default"]


async def get_text(key: str, db: AsyncSession | None = None, **kwargs: Any) -> str:
    """Load text by *key*: DB value overrides built-in default.

    Any extra ``kwargs`` are interpolated via ``str.format_map``.
    """
    entry = SYSTEM_TEXTS.get(key)
    if not entry:
        logger.warning("Unknown system text key requested: %s", key)
        return key

    template: str | None = None

    try:
        if db is not None:
            row = await db.scalar(
                select(BotContent.value).where(BotContent.key == key)
            )
            if row:
                template = row
        else:
            async with SessionLocal() as session:
                row = await session.scalar(
                    select(BotContent.value).where(BotContent.key == key)
                )
                if row:
                    template = row
    except Exception:
        logger.exception("Failed to load text '%s' from DB, using default", key)

    if template is None:
        template = entry["default"]

    if kwargs:
        try:
            return template.format_map(kwargs)
        except (KeyError, ValueError):
            logger.warning("Failed to interpolate text '%s' with %s", key, kwargs)
            return template

    return template


def list_system_texts() -> list[dict[str, Any]]:
    """Return metadata for all registered system texts (for admin UI)."""
    result = []
    for key, meta in SYSTEM_TEXTS.items():
        result.append({
            "key": key,
            "label": meta["label"],
            "group": meta["group"],
            "description": meta["description"],
            "default": meta["default"],
            "supports_html": meta["supports_html"],
            "variables": meta.get("variables", []),
        })
    return result
