"""
Реализация возможности отправки логов в Telegram чат

logger.info("...") -> только в консоль
logger.warning("...") -> в консоль и Telegram
logger.error("...") -> в консоль и Telegram
"""

import logging
import asyncio
from aiogram import Bot
from typing import Optional

class TelegramHandler(logging.Handler):
    """
    Логгер для отправки выбранных сообщений в Telegram.
    """

    def __init__(self, bot: Bot, chat_id: int, loop: Optional[asyncio.AbstractEventLoop] = None, level=logging.INFO):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id
        self.loop = loop or asyncio.get_event_loop()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            asyncio.run_coroutine_threadsafe(
                self.bot.send_message(self.chat_id, msg),
                self.loop
            )
        except Exception:
            self.handleError(record)
