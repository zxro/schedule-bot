from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    @brief Настройки бота, загружаемые из переменных окружения

    @field BOT_TOKEN Токен Telegram-бота
    @field TELEGRAM_LOG_CHAT_ID Чат для логов

    @field DB_TIMETABLE_URL URL для подключения к базе данных

    @field TIMETABLE_API_BASE URL для получения расписания по каждому факультету
    @field REQUEST_CONCURRENCY Ограничения числа одновременно выполняющихся запросов
    @field REQUEST_DELAY Пуза между запросами
    @field MAX_RETRIES Максимальное количество повторов запросов
    @field RETRY_BACKOFF_FACTOR

    @field CLASSES Расписание занятий
    @field RETAKE Расписание пересдач
    """

    TELEGRAM_BOT_TOKEN: str = Field(..., env='TELEGRAM_BOT_TOKEN')
    TELEGRAM_LOG_CHAT_ID: int = Field(..., env='TELEGRAM_LOG_CHAT_ID')

    TIMETABLE_API_BASE: str = Field(..., env='TIMETABLE_API_BASE')
    DB_TIMETABLE_URL: str = Field(..., env='DB_TIMETABLE_URL')

    REQUEST_CONCURRENCY: int = Field(..., env='REQUEST_CONCURRENCY')
    REQUEST_DELAY: float = Field(..., env='REQUEST_DELAY')
    MAX_RETRIES: int = Field(..., env='MAX_RETRIES')
    RETRY_BACKOFF_FACTOR: float = Field(..., env='RETRY_BACKOFF_FACTOR')

    CLASSES: str = Field(..., env='CLASSES')
    RETAKE: str = Field(..., env='RETAKE')

settings = Settings()
