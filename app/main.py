import asyncio

from app.bot import bot, dp
from app.custom_logging.TelegramLogHandler import send_chat_info_log
from app.custom_logging.setup import setup_logging
from app.database.db import startup
from app.handlers.init_handlers import register_handlers



async def main():
    """
    @brief Главная функция запуска бота.

    @details:
        - Проверяет и создает БД при необходимости
        - Создает объект Bot и Dispatcher
        - Регистрирует роутеры с обработчиками сообщений и callback
        - Запускает polling для обработки сообщений Telegram
        - Запускает логирование
    """

    logger = setup_logging(bot)

    await startup()

    register_handlers(dp)

    logger.info("Бот успешно запущен")
    await send_chat_info_log(bot, "Бот успешно запущен")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())