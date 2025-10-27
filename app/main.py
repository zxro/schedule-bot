import asyncio
import logging

from app.bot.bot import dp, bot
from app.bot.on_shutdown import on_shutdown
from app.bot.on_startup import on_startup
from app.bot.safe_pooling import safe_polling

logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота."""

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await safe_polling()
    finally:
        await bot.session.close()
        logger.info("✅ Сессия Telegram API закрыта.")

if __name__ == "__main__":
    asyncio.run(main())