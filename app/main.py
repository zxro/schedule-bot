import asyncio

from aiogram import Bot, Dispatcher
from app.config import settings
from app.custom_logging.setup import setup_logging
from app.handlers.init_handlers import register_handlers

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

async def main():
    """
    @brief Главная функция запуска бота.

    @details:
        - Создает объект Bot и Dispatcher
        - Регистрирует роутеры с обработчиками сообщений и callback
        - Запускает polling для обработки сообщений Telegram
        - Запускает логирование
    """

    logger = setup_logging(bot)

    register_handlers(dp)

    logger.info("Бот успешно запущен")
    await bot.send_message(settings.TELEGRAM_LOG_CHAT_ID, text="Бот успешно запущен")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

