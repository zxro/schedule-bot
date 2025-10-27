import asyncio

from app.bot.bot import dp, bot
from app.bot.on_startup import on_startup


async def main():
    """Главная функция запуска бота."""

    dp.startup.register(on_startup)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())