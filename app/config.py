from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    @brief Настройки бота, загружаемые из переменных окружения

    @field BOT_TOKEN Токен Telegram-бота
    """
    BOT_TOKEN: str = Field(..., env='BOT_TOKEN')

settings = Settings()
