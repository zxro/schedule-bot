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

engine = create_async_engine(settings.DB_TIMETABLE_URL, future=True, echo=False, pool_size=10, max_overflow=20)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
