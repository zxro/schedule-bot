import logging
import contextvars

current_user_id = contextvars.ContextVar("current_user_id", default="N/A")
current_username = contextvars.ContextVar("current_username", default="N/A")


class ContextFilter(logging.Filter):
    """
    Добавляет user_id и username из contextvars в каждый лог.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.user_id = current_user_id.get()
        record.username = current_username.get()
        return True