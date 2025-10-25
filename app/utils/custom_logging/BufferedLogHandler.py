"""
Хранит последние N логов в памяти и позволяет экспортировать их в файл.
Используется совместно с TelegramLogHandler.
"""

import logging
from io import BytesIO
from collections import deque


class BufferedLogHandler(logging.Handler):
    """
    Обработчик логов, сохраняющий последние N записей в памяти.

    Используется для получения контекста при ошибках.
    """

    def __init__(self, capacity: int = 500):
        super().__init__()
        self.capacity = capacity
        self.buffer: deque[logging.LogRecord] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord):
        """Добавляет запись в буфер (старые записи автоматически удаляются)."""
        self.buffer.append(record)

    def get_logs_as_text(self, formatter: logging.Formatter | None = None) -> str:
        """
        Возвращает буфер логов в виде одной текстовой строки.

        Аргументы:
            formatter : logging.Formatter | None
            Форматтер для логов. Если None, используется стандартный формат.

        Возвращает:
            str : все записи из буфера, объединённые в одну строку
        """

        fmt = formatter or logging.Formatter(
            "%(asctime)s [%(levelname)s] "
            "[u_id=%(user_id)s u_n=@%(username)s] "
            "%(name)s: %(message)s"
        )

        return "\n".join(fmt.format(record) for record in self.buffer)

    def get_logs_as_file(self, formatter: logging.Formatter | None = None) -> BytesIO:
        """
        Возвращает буфер логов как BytesIO-файл для отправки в Telegram.

        Аргументы:
            formatter : logging.Formatter | None
            Форматтер для логов.

        Возвращает:
            BytesIO : файл с содержимым буфера
        """

        file_bytes = BytesIO()
        file_bytes.write(self.get_logs_as_text(formatter).encode("utf-8"))
        file_bytes.seek(0)
        return file_bytes

global_buffer_handler = BufferedLogHandler(capacity=500)