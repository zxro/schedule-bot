"""
Реализует пользовательский обработчик логов для Python logging,
который асинхронно отправляет сообщения в Telegram-чат.
Встроена защита от спама (rate-limiting) и поддержка длинных сообщений.

- Асинхронная очередь для логов.
- Ограничение длины сообщений (4000 символов).
- Повторная попытка при ошибке отправки.
"""
from datetime import datetime
import logging
import asyncio
from aiogram import Bot
from asyncio import Queue
from app.config import settings

class TelegramLogHandler(logging.Handler):
    """
    Асинхронный обработчик логов для отправки сообщений в Telegram.

    Особенности:
    - Работает через очередь asyncio.Queue
    - Сообщения дробятся на части, если превышают 4000 символов
    - Между сообщениями выдерживается RATE_LIMIT

    Поля:
    MAX_MESSAGE_LENGTH : int
        Максимальная длина одного сообщения в Telegram.
    RATE_LIMIT : float
        Минимальная задержка между отправками сообщений (секунды).
    _queue : asyncio.Queue
        Очередь сообщений для отправки.
    _worker_task : asyncio.Task | None
        Задача фонового воркера.
    """

    MAX_MESSAGE_LENGTH = 4000
    RATE_LIMIT = 1.0

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
        """

        while True:
            message = await self._queue.get()
            sent = False
            while not sent:
                try:
                    await self.bot.send_message(self.chat_id, message)
                    sent = True
                except Exception as e:
                    logging.warning(
                        f"Не удалось отправить логи в Telegram, повторная попытка через 21 секунду.\n Текст: {message}"
                    )
                    await asyncio.sleep(21)

            await asyncio.sleep(self.RATE_LIMIT)
            self._queue.task_done()

    def emit(self, record: logging.LogRecord):
        """
        Форматирует запись лога и помещает её в очередь на отправку.
        Если сообщение слишком длинное -> разбивается на части.
        """

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

async def send_chat_info_log(bot: Bot, text: str):
    """
    Отправляет информационный лог уровня INFO напрямую в Telegram-чат.
    Используется вручную для редких сообщений (например, уведомлений об операциях).

    Аргументы:
    bot : aiogram.Bot
        Экземпляр бота.
    text : str
        Текст сообщения.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    formatted_text = f"{timestamp} [INFO] {text}"
    await bot.send_message(settings.TELEGRAM_LOG_CHAT_ID, text=formatted_text)