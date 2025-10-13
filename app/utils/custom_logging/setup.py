"""
Конфигурирует систему логирования для проекта.
Логи отправляются в консоль и (при уровне WARNING и выше) в Telegram.

- INFO → только консоль
- WARNING и ERROR → консоль + Telegram
"""

import logging
from aiogram import Bot
from app.config import settings
from app.utils.custom_logging.ContextFilter import ContextFilter
from app.utils.custom_logging.TelegramLogHandler import TelegramLogHandler

def setup_logging(bot: Bot) -> logging.Logger:
    """
    Настройка логирования приложения.

    Параметры:
    bot : aiogram.Bot
        Экземпляр Telegram-бота для отправки логов в чат.

    Возвращает:
    logging.Logger
        Root-логгер с двумя обработчиками:
        - ConsoleHandler (INFO+)
        - TelegramLogHandler (WARNING+)
    """

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    context_filter = ContextFilter()

    log_format = (
        "%(asctime)s [%(levelname)s] "
        "[u_id=%(user_id)s u_n=@%(username)s] "
        "%(name)s: %(message)s"
    )

    # --- консоль ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.addFilter(context_filter)
    logger.addHandler(console_handler)

    # --- телеграм ---
    tg_handler = TelegramLogHandler(bot, settings.TELEGRAM_LOG_CHAT_ID, level=logging.WARNING)
    tg_handler.setFormatter(logging.Formatter(log_format))
    tg_handler.addFilter(context_filter)
    logger.addHandler(tg_handler)

    return logger