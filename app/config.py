from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """
    Настройки бота, загружаемые из переменных окружения.

    Атрибуты:
        BOT_TOKEN (str): Токен Telegram-бота.
    """

    BOT_TOKEN: str = Field(..., env='BOT_TOKEN')

settings = Settings()