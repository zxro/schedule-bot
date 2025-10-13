import asyncio

from app.bot import bot, dp
from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log
from app.utils.custom_logging.setup import setup_logging
from app.database.db import checking_db
from app.handlers.init_handlers import register_handlers
from app.utils.week_mark import init_week_mark, update_week_mark
from app.middlewares.UserContextMiddleware import UserContextMiddleware

async def on_startup():
    """Настройка бота перед запуском"""

    logger = setup_logging(bot)

    await checking_db()

    dp.message.middleware(UserContextMiddleware())
    dp.callback_query.middleware(UserContextMiddleware())

    register_handlers(dp)

    await init_week_mark()
    asyncio.create_task(update_week_mark())

    logger.info("Бот успешно запущен")
    await send_chat_info_log(bot, "Бот успешно запущен")



async def main():
    """Главная функция запуска бота."""

    dp.startup.register(on_startup)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())