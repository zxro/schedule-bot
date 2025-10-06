from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.database import models
import logging

logger = logging.getLogger(__name__)

async def init_db(eng: AsyncEngine):
    """
    Проверяет доступность базы данных и создаёт таблицы из models.Base.

    Логика:
        - Пытается открыть транзакцию через engine.begin().
        - Если база доступна — логирует успех.
        - Если база недоступна (OperationalError), создаёт все таблицы.
    """
    try:
        async with eng.begin() as conn:
            pass
        logger.info("Подключение к базе данных успешно.")
    except OperationalError:
        logger.warning("Не удалось подключиться к базе. Создание базы и таблиц...")

        async with eng.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("База данных и таблицы созданы.")