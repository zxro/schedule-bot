import asyncio
import logging

from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError

from app.bot.bot import bot, dp
from app.keyboards.init_keyboards import refresh_all_keyboards
from app.keyboards.sync_kb import refresh_sync_keyboards
from app.utils.admins.admin_list import refresh_admin_list, check_admins_start
from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log
from app.utils.custom_logging.setup_log import setup_logging
from app.database.db import checking_db
from app.handlers.init_handlers import register_handlers
from app.utils.schedule.auto_sync import schedule_sync_task
from app.utils.schedule.search_professors import update_professors_cache
from app.utils.week_mark.week_mark import init_week_mark, update_week_mark
from app.middlewares.UserContextMiddleware import UserContextMiddleware

logger = logging.getLogger(__name__)

async def on_startup():
    """Настройка бота перед запуском"""

    setup_logging(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except (TelegramNetworkError, TelegramUnauthorizedError) as e:
        logger.warning(f"⚠️ Не удалось удалить webhook: {e}")
    except Exception as e:
        logger.warning(f"⚠️ Неизвестная ошибка при удалении webhook: {e}")

    try:
        await checking_db()
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке базы данных: {e}")

    try:
        await refresh_sync_keyboards()
        await refresh_all_keyboards()
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении клавиатур: {e}")

    try:
        await refresh_admin_list()
        await check_admins_start()
    except Exception as e:
        logger.error(f"❌ Ошибка при работе с администраторами: {e}")

    dp.message.middleware(UserContextMiddleware())
    dp.callback_query.middleware(UserContextMiddleware())

    register_handlers(dp)

    await init_week_mark()

    asyncio.create_task(update_week_mark())
    asyncio.create_task(schedule_sync_task())

    try:
        await asyncio.wait_for(update_professors_cache(), timeout=90)
    except asyncio.TimeoutError:
        logger.warning("⚠️ Обновление кэша преподавателей превысило 90 секунд.")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении кэша преподавателей: {e}")

    logger.info("✅ Бот успешно запущен")
    try:
        await send_chat_info_log("✅ Бот успешно запущен")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить лог запуска в Telegram: {e}")