import asyncio
import logging
from aiogram.exceptions import TelegramUnauthorizedError, TelegramNetworkError
from app.bot.bot import dp, bot

logger = logging.getLogger(__name__)

async def safe_polling():
    """Цикл безопасного polling с перезапуском при временных ошибках."""

    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
            break
        except TelegramUnauthorizedError:
            logger.critical("❌ Ошибка авторизации Telegram — неверный токен.")
            print("❌ Telegram отклонил токен. Проверьте TELEGRAM_BOT_TOKEN.")
            break
        except TelegramNetworkError:
            logger.error(f"⚠️ Ошибка сети при обращении к Telegram API. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"⚠️ Необработанная ошибка в polling, перезапуск через 3 секунды. Ошибка: {e}")
            await asyncio.sleep(3)