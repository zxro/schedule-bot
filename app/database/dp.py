"""
Асинхронная настройка работы с базой данных PostgreSQL через SQLAlchemy.

Содержит:
1. Асинхронный движок подключения к базе данных.
2. Фабрику асинхронных сессий для работы с БД.
3. Вспомогательную функцию для получения сессии в асинхронном контексте.

Используется:
- asyncpg в качестве драйвера PostgreSQL.
- SQLAlchemy ORM для работы с моделями и запросами.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy.pool import AsyncAdaptedQueuePool

engine = create_async_engine(
    settings.DB_TIMETABLE_URL,        # строка подключения к PostgreSQL
    echo=False,                       # echo=True = логировать SQL-запросы в консоль
    future=True,                      # новый API SQLAlchemy 2.0
    poolclass=AsyncAdaptedQueuePool,  # включаем пул соединений
    pool_size=10,                     # держим до 10 соединений открытыми
    max_overflow=20                   # создаётся ещё 20 соединений при пике нагрузки
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncSession:
    """
    Возвращает новую асинхронную сессию для работы с базой данных.

    Пример использования:
        async with get_session() as session:
            await session.execute(...)
            await session.commit()

    Возвращает:
        AsyncSession: объект асинхронной сессии SQLAlchemy
    """

    return AsyncSessionLocal()
