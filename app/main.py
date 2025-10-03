import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.config import settings
from app.custom_logging.TelegramHandler import TelegramHandler
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

    chat_id = settings.TELEGRAM_LOG_CHAT_ID

    logger = logging.getLogger("my_app")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("[%(levelname)s] %(message)s")

    telegram_handler = TelegramHandler(bot, chat_id)
    telegram_handler.setFormatter(formatter)
    telegram_handler.setLevel(logging.WARNING)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(telegram_handler)
    logger.addHandler(console_handler)

    register_handlers(dp)

    logger.info("bot start")
    await bot.send_message(settings.TELEGRAM_LOG_CHAT_ID, text="Бот успешно запущен")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

