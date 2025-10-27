import asyncio
import logging

from app.bot.bot import bot
from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log

logger = logging.getLogger(__name__)


async def on_shutdown():
    """Завершение работы бота и очистка ресурсов."""

    logger.info("🛑 Завершение работы бота...")

    # Закрываем все фоновые задачи
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        logger.info(f"⏳ Завершаем {len(pending)} фоновых задач...")
        for task in pending:
            task.cancel()
        try:
            await asyncio.gather(*pending, return_exceptions=True)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при завершении фоновых задач: {e}")

    # Закрываем сессию Telegram API
    try:
        await bot.session.close()
        logger.info("✅ Сессия Telegram API закрыта.")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при закрытии сессии Telegram API: {e}")

    logger.info("✅ Завершение работы бота выполнено.")
    try:
        await send_chat_info_log("✅ Завершение работы бота выполнено.")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить лог завершения работы в Telegram: {e}")