"""
Реализация возможности отправки логов в Telegram чат

logger.info("...") -> только в консоль
logger.warning("...") -> в консоль и Telegram
logger.error("...") -> в консоль и Telegram
"""

import logging
import asyncio
from aiogram import Bot
from asyncio import Queue

from app.config import settings


class TelegramLogHandler(logging.Handler):
    """
    Асинхронный логгер для отправки сообщений в Telegram с rate-limiting.
    """

    MAX_MESSAGE_LENGTH = 4000
    RATE_LIMIT = 1.0

    _queue: Queue
    _worker_task: asyncio.Task | None = None

    def __init__(self, bot: Bot, chat_id: int, level=logging.WARNING):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id
        self._queue = Queue()
        self._start_worker()

    def _start_worker(self):
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            message = await self._queue.get()
            sent = False
            while not sent:
                try:
                    await self.bot.send_message(self.chat_id, message)
                    sent = True
                except Exception as e:
                    await asyncio.sleep(21)

            await asyncio.sleep(self.RATE_LIMIT)
            self._queue.task_done()

    def emit(self, record: logging.LogRecord):
        try:
            log_entry = self.format(record)
            messages = self._split_message(log_entry)
            for idx, chunk in enumerate(messages, 1):
                if len(messages) > 1:
                    chunk = f"[{idx}/{len(messages)}] {chunk}"
                self._queue.put_nowait(chunk)
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