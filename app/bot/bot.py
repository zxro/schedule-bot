import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError, TelegramNetworkError
from aiogram.utils.token import TokenValidationError

from app.config import settings

logger = logging.getLogger(__name__)

try:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(bot=bot)

except (ValueError, TokenValidationError):
    logger.critical("❌ Ошибка при инициализации бота: неверный формат токена.")
    print("❌ Ошибка: неверный токен Telegram. Проверьте TELEGRAM_BOT_TOKEN.")
    sys.exit(1)

except TelegramUnauthorizedError:
    logger.critical("❌ Ошибка: Telegram API отклонил токен — Unauthorized.")
    print("❌ Ошибка: неверный токен Telegram. Бот остановлен.")
    sys.exit(1)

except TelegramNetworkError:
    logger.critical("❌ Ошибка сети при подключении к Telegram API.")
    print("❌ Ошибка: нет соединения с Telegram API.")
    sys.exit(1)

except Exception as e:
    logger.critical(f"❌ Неизвестная ошибка при создании бота: {e}")
    print(f"❌ Ошибка при создании бота: {e}")
    sys.exit(1)