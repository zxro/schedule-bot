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

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from sqlalchemy.pool import AsyncAdaptedQueuePool

engine = create_async_engine(
    settings.DB_TIMETABLE_URL,        # строка подключения к PostgreSQL
    echo=False,                       # echo=True = логировать SQL-запросы в консоль
    future=True,                      # новый API SQLAlchemy 2.0
    poolclass=AsyncAdaptedQueuePool,  # пул соединений
    pool_size=10,                     # держим до 10 соединений открытыми
    max_overflow=20                   # создаётся ещё 20 соединений при пике нагрузки
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)