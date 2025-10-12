from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine
from app.database import models
import logging
from app.bot import bot
from app.custom_logging.TelegramLogHandler import send_chat_info_log

logger = logging.getLogger(__name__)
# Добавим создание таблицы users при инициализации
async def init_db(eng: AsyncEngine):
    """
    Проверяет подключение к SQLite и наличие таблиц.
    Создаёт только отсутствующие таблицы из models.Base.
    """
    try:
        async with eng.begin() as conn:
            existing_tables = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        model_tables = set(models.Base.metadata.tables.keys())
        missing_tables = model_tables - existing_tables

        if missing_tables:
            logger.warning(f"⚠️ Отсутствуют таблицы: {missing_tables}. Создаём их...")
            async with eng.begin() as conn:
                tables_to_create = [models.Base.metadata.tables[name] for name in missing_tables]
                await conn.run_sync(lambda sync_conn: models.Base.metadata.create_all(sync_conn, tables=tables_to_create))
            logger.info(f"✅ Таблицы {missing_tables} успешно созданы.")
            await send_chat_info_log(bot, f"✅ Таблицы {missing_tables} успешно созданы.")
        else:
            logger.info("✅ Все таблицы существуют.")

    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации базы: {e}")
        raise