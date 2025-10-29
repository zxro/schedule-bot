import logging
import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

base_dir = Path(__file__).resolve().parent.parent
dotenv_path = base_dir / "config" / ".env"
if not dotenv_path.exists():
    logger.critical(f".env the file was not found on the way: {dotenv_path}")
    sys.exit(1)

load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    """
    Настройки бота, загружаемые из переменных окружения

    Поля:
        TELEGRAM_BOT_TOKEN: Токен Telegram-бота
        TELEGRAM_LOG_CHAT_ID: Чат для логов
        ADMIN_PASSWORD: Пароль для подтверждения действий

        TIMETABLE_API_BASE: URL для подключения к сайту университета
        DB_TIMETABLE_URL: URL для подключения к базе данных
        LIST_ADMINS_URL: URL для списка администраторов

        REQUEST_CONCURRENCY: Ограничения числа одновременно выполняющихся запросов
        REQUEST_DELAY: Пауза между запросами
        MAX_RETRIES: Максимальное количество повторов запросов
        RETRY_BACKOFF_FACTOR: Множитель для экспоненциальной задержки

        CLASSES: Тип расписания: занятия
        RETAKE: Тип расписания: пересдачи
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DB_TIMETABLE_URL:
            db_path = base_dir / "data" / "TimetableTvSU.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.DB_TIMETABLE_URL = f"sqlite+aiosqlite:///{db_path}"

    TELEGRAM_BOT_TOKEN: str = Field(default=..., validation_alias='TELEGRAM_BOT_TOKEN')
    TELEGRAM_LOG_CHAT_ID: int = Field(default=..., validation_alias='TELEGRAM_LOG_CHAT_ID')
    ADMIN_PASSWORD: str = Field(default=..., validation_alias='ADMIN_PASSWORD')

    TIMETABLE_API_BASE: str = Field(default=..., validation_alias='TIMETABLE_API_BASE')
    DB_TIMETABLE_URL: str = Field(default="")

    REQUEST_CONCURRENCY: int = Field(default=..., validation_alias='REQUEST_CONCURRENCY')
    REQUEST_DELAY: float = Field(default=..., validation_alias='REQUEST_DELAY')
    MAX_RETRIES: int = Field(default=..., validation_alias='MAX_RETRIES')
    RETRY_BACKOFF_FACTOR: float = Field(default=..., validation_alias='RETRY_BACKOFF_FACTOR')

    CLASSES: str = Field(default=..., validation_alias='CLASSES')
    RETAKE: str = Field(default=..., validation_alias='RETAKE')

try:
    settings = Settings()
except Exception as e:
    logger.critical(f"❌ Ошибка загрузки настроек: {e}")
    sys.exit(1)