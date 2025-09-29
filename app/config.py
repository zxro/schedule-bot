from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

## @brief Найстрйоки бота, загружаемые из переменных окружения
#  @var BOT_TOKEN Токен Telegram-бота
class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., env='BOT_TOKEN')

settings = Settings()
