from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

from sys import exit

base_dir = Path(__file__).resolve().parent.parent
dotenv_path = base_dir / "config" / ".env"
if not dotenv_path.exists():
    exit(".env file not found in config/.env")
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    """
    @brief Настройки бота, загружаемые из переменных окружения

    @field BOT_TOKEN Токен Telegram-бота
    @field TELEGRAM_LOG_CHAT_ID Чат для логов

    @field TIMETABLE_API_BASE URL для подключения к сайту университета
    @field DB_TIMETABLE_URL URL для подключения к базе данных

    @field REQUEST_CONCURRENCY Ограничения числа одновременно выполняющихся запросов
    @field REQUEST_DELAY Пуза между запросами
    @field MAX_RETRIES Максимальное количество повторов запросов
    @field RETRY_BACKOFF_FACTOR Множитель для экспоненциальной задержки

    @field CLASSES Расписание занятий
    @field RETAKE Расписание пересдач
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DB_TIMETABLE_URL:
            db_path = base_dir / "data" / "TimetableTvSU.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.DB_TIMETABLE_URL = f"sqlite+aiosqlite:///{db_path}"

    TELEGRAM_BOT_TOKEN: str = Field(..., validation_alias='TELEGRAM_BOT_TOKEN')
    TELEGRAM_LOG_CHAT_ID: int = Field(..., validation_alias='TELEGRAM_LOG_CHAT_ID')
    ADMIN_PASSWORD: str = Field(..., validation_alias='ADMIN_PASSWORD')

    TIMETABLE_API_BASE: str = Field(..., validation_alias='TIMETABLE_API_BASE')
    DB_TIMETABLE_URL: str = Field(default="")
    LIST_ADMINS_URL: str = Field(default="")

    REQUEST_CONCURRENCY: int = Field(..., validation_alias='REQUEST_CONCURRENCY')
    REQUEST_DELAY: float = Field(..., validation_alias='REQUEST_DELAY')
    MAX_RETRIES: int = Field(..., validation_alias='MAX_RETRIES')
    RETRY_BACKOFF_FACTOR: float = Field(..., validation_alias='RETRY_BACKOFF_FACTOR')

    CLASSES: str = Field(..., validation_alias='CLASSES')
    RETAKE: str = Field(..., validation_alias='RETAKE')

settings = Settings()
