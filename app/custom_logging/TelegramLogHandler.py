"""
Реализация возможности отправки логов в Telegram чат

logger.info("...") -> только в консоль
logger.warning("...") -> в консоль и Telegram
logger.error("...") -> в консоль и Telegram
"""

import logging
from aiogram import Bot

from app.config import settings


class TelegramLogHandler(logging.Handler):
    """
    Логгер для отправки выбранных сообщений в Telegram.
    """

    def __init__(self, bot: Bot, chat_id: int, level=logging.WARNING):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self.format(record)
            import asyncio
            asyncio.create_task(self.bot.send_message(self.chat_id, log_entry))
        except Exception:
            self.handleError(record)

async def send_chat_info_log(bot: Bot, text: str):
    """
    Отправляет информационный лог (уровня INFO) в чат логов.
    Используется вручную для редких сообщений.
    """
    await bot.send_message(settings.TELEGRAM_LOG_CHAT_ID, text=f"[INFO] {text}")