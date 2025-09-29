import asyncio
from aiogram import Bot, Dispatcher
from app.config import settings
from app.handlers import register_handlers


async def main():
    """
    Главная функция запуска бота.

    Действия:
        - Создает объект Bot и Dispatcher
        - Регистрирует роутеры с обработчиками сообщений и callback
        - Запускает polling для обработки сообщений Telegram
    """

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    register_handlers(dp)

    print("Бот запущен!")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
