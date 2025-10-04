"""
Реализация возможности отправки логов в Telegram чат

logger.info("...") -> только в консоль
logger.warning("...") -> в консоль и Telegram
logger.error("...") -> в консоль и Telegram
"""

from app.config import settings
import logging
import asyncio
from aiogram import Bot

class TelegramLogHandler(logging.Handler):
    """
    Логгер для отправки сообщений в Telegram с ограничением длины
    и нумерацией частей для длинных логов.
    """

    MAX_MESSAGE_LENGTH = 4000

    def __init__(self, bot: Bot, chat_id: int, level=logging.WARNING):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self.format(record)

            if len(log_entry) <= self.MAX_MESSAGE_LENGTH:
                asyncio.create_task(self.bot.send_message(self.chat_id, log_entry))
            else:
                chunks = self._split_message(log_entry)
                total = len(chunks)
                for idx, chunk in enumerate(chunks, 1):
                    numbered_chunk = f"[{idx}/{total}] {chunk}"
                    asyncio.create_task(self.bot.send_message(self.chat_id, numbered_chunk))

        except Exception:
            self.handleError(record)

    def _split_message(self, message: str):
        """
        Разбивает длинное сообщение на части, учитывая MAX_MESSAGE_LENGTH.
        """
        chunks = []
        start = 0
        while start < len(message):
            end = start + self.MAX_MESSAGE_LENGTH
            chunks.append(message[start:end])
            start = end
        return chunks


async def send_chat_info_log(bot: Bot, text: str):
    """
    Отправляет информационный лог (уровня INFO) в чат логов.
    Используется вручную для редких сообщений.
    """
    await bot.send_message(settings.TELEGRAM_LOG_CHAT_ID, text=f"[INFO] {text}")