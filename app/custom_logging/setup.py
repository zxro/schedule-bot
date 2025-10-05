"""
Конфигурирует систему логирования для проекта.
Логи отправляются в консоль и (при уровне WARNING и выше) в Telegram.

- INFO → только консоль
- WARNING и ERROR → консоль + Telegram
"""

import logging
from aiogram import Bot
from app.config import settings
from app.custom_logging.TelegramLogHandler import TelegramLogHandler

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

    # --- консоль ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(console_handler)

    # --- телеграм ---
    tg_handler = TelegramLogHandler(bot, settings.TELEGRAM_LOG_CHAT_ID, level=logging.WARNING)
    tg_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(tg_handler)

    return logger