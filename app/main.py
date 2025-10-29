import asyncio
import logging

from app.bot.bot import dp
from app.bot.on_shutdown import on_shutdown
from app.bot.on_startup import on_startup
from app.bot.safe_polling import safe_polling

logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота."""

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await safe_polling()
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка в main: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as err:
        logger.critical(f"❌ Критическая ошибка при работе бота: {err}")