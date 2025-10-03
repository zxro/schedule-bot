import asyncio
from aiogram import Bot, Dispatcher
from app.config import settings
from app.handlers import register_handlers
from app.database.database import Database


async def main():
    """
    Главная функция запуска бота.

    Действия:
        - Создает объект Bot и Dispatcher
        - Инициализирует подключение к БД
        - Регистрирует роутеры с обработчиками сообщений и callback
        - Запускает polling для обработки сообщений Telegram
    """
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Инициализация базы данных
    db = Database(settings.DATABASE_URL)
    await db.connect()

    # Передаем объект БД в диспетчер
    dp["db"] = db

    register_handlers(dp)

    print("Бот запущен!")

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())