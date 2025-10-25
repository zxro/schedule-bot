"""
Реализует пользовательский обработчик логов для Python logging,
который асинхронно отправляет сообщения в Telegram-чат.
Встроена защита от спама (rate-limiting), поддержка длинных сообщений
и буфер последних записей для контекста при ошибках.

Функциональность:
- Асинхронная очередь для логов.
- Ограничение длины сообщений (4000 символов).
- Повторная попытка при ошибке отправки.
- Хранение последних N логов в памяти.
- При ошибке отправляются: буфер последних логов + сам файл ошибки.
"""

from datetime import datetime
import logging
import asyncio
from io import BytesIO

from aiogram import Bot
from asyncio import Queue

from app.bot import bot as bot_info_log
from app.config import settings
from aiogram.types import BufferedInputFile
from app.utils.custom_logging.BufferedLogHandler import global_buffer_handler


class TelegramLogHandler(logging.Handler):
    """
    Асинхронный обработчик логов для отправки сообщений в Telegram.

    Особенности:
    - Работает через очередь asyncio.Queue.
    - Сообщения дробятся на части, если превышают 4000 символов.
    - Между сообщениями выдерживается RATE_LIMIT.
    - При ошибках (ERROR+) отправляются:
        • recent_logs.txt — последние логи
        • error_<timestamp>.txt — сам лог ошибки

    Поля:
    MAX_MESSAGE_LENGTH : int
        Максимальная длина одного сообщения в Telegram.
    RATE_LIMIT : float
        Минимальная задержка между отправками сообщений (секунды).
    TIME_LIMIT : int
        Задержка между повторными попытками при ошибке
    _queue : asyncio.Queue
        Очередь сообщений для отправки.
    _worker_task : asyncio.Task | None
        Задача фонового воркера.
    """

    MAX_MESSAGE_LENGTH = 4000
    RATE_LIMIT = 1.0
    TIME_SLEEP = 21  # задержка между повторными попытками при ошибке

    _queue: Queue
    _worker_task: asyncio.Task | None = None

    def __init__(self, bot: Bot, chat_id: int, level=logging.WARNING):
        """
        Параметры:
        bot : aiogram.Bot
            Экземпляр бота для отправки сообщений.
        chat_id : int
            ID чата, куда будут отправляться логи.
        level : int
            Минимальный уровень логов (по умолчанию WARNING).
        """

        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id
        self._queue = Queue()
        self._start_worker()

    def _start_worker(self):
        """
        Запускает фоновую задачу-воркер, если она ещё не запущена.

        - Проверяет наличие self._worker_task; если оно пусто, создаёт задачу
            asyncio.create_task(self._worker()) и сохраняет её в self._worker_task.
        """

        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        """
        Фоновый воркер последовательно отправляет сообщения из очереди в Telegram.

        Логика работы:
            1. Бесконечный цикл: ждём сообщение из self._queue (await self._queue.get()).
            2. Пытаемся отправить сообщение через await self.bot.send_message(self.chat_id, message).
               - При успешной отправке помечаем sent = True.
               - При ошибке — ждем фиксированное время (21 сек) и пробуем снова (повторные попытки).
            3. После успешной отправки делаем await asyncio.sleep(self.RATE_LIMIT) — соблюдение rate-limit.
            4. Вызываем self._queue.task_done() для уведомления об обработке элемента очереди.
            5. Переходим к следующему сообщению.

        Особенности реализации:
            - Повторная попытка при любом исключении.
            - Фиксированная пауза при ошибке отправки (21 сек).
            - Ошибки типа error и выше отправляются в файлом
        """

        while True:
            item = await self._queue.get()
            sent = False

            while not sent:
                try:
                    if isinstance(item, str):
                        await self.bot.send_message(self.chat_id, item)

                    elif isinstance(item, dict) and item.get("as_file"):
                        file_bytes: BytesIO = item["file"]
                        caption = item.get("caption", "Ошибка")
                        filename = item.get("filename", "error_log.txt")

                        file_bytes.seek(0)
                        input_file = BufferedInputFile(file_bytes.getvalue(), filename=filename)

                        await self.bot.send_document(
                            chat_id=self.chat_id,
                            document=input_file,
                            caption=caption,
                            disable_notification=False,
                        )

                    sent = True

                except Exception as e:
                    logging.warning(
                        f"Не удалось отправить лог в Telegram, повторная попытка через {self.TIME_SLEEP} секунду.\nОшибка: {e}",
                    )
                    await asyncio.sleep(self.TIME_SLEEP)

            await asyncio.sleep(self.RATE_LIMIT)
            self._queue.task_done()

    def emit(self, record: logging.LogRecord):
        """
        Форматирует запись лога и помещает её в очередь на отправку.
        Если уровень — ERROR или CRITICAL, лог сохраняется в файл и отправляется как документ.
        """

        try:
            log_entry = self.format(record)

            # --- ERROR и выше ---
            if record.levelno >= logging.ERROR:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

                # Отправка буфера последних логов
                buffer_file = global_buffer_handler.get_logs_as_file(self.formatter)
                self._queue.put_nowait({
                    "as_file": True,
                    "file": buffer_file,
                    "filename": "recent_logs.txt",
                    "caption": f"Последние {global_buffer_handler.capacity} логов перед ошибкой",
                })

                # Отправка лога ошибки
                error_file = BytesIO()
                error_file.write(log_entry.encode("utf-8"))
                self._queue.put_nowait({
                    "as_file": True,
                    "file": error_file,
                    "filename": f"error_{timestamp}.txt",
                    "caption": f"Ошибка уровня {record.levelname}"
                })
                return

            # --- INFO / WARNING ---
            messages = self._split_message(log_entry)
            for idx, chunk in enumerate(messages, 1):
                if len(messages) > 1:
                    chunk = f"[{idx}/{len(messages)}] {chunk}"
                self._queue.put_nowait(chunk)

        except Exception:
            self.handleError(record)

    def _split_message(self, message: str):
        """
        Разбивает сообщение на части по MAX_MESSAGE_LENGTH символов.

        Параметры:
        message : str
            Исходное сообщение.

        Возвращает:
        list[str]
            Список частей сообщения.
        """

        chunks = []
        start = 0
        while start < len(message):
            end = start + self.MAX_MESSAGE_LENGTH
            chunks.append(message[start:end])
            start = end
        return chunks

async def send_chat_info_log(text: str):
    """
    Отправляет информационный лог уровня INFO напрямую в Telegram-чат.
    Используется вручную для редких сообщений (например, уведомлений об операциях).

    Аргументы:
        text : str
            Текст сообщения.
    """

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    formatted_text = f"{timestamp} [INFO] {text}"
    await bot_info_log.send_message(settings.TELEGRAM_LOG_CHAT_ID, text=formatted_text)