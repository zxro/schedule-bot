"""
Асинхронная настройка работы с базой данных SQLite через SQLAlchemy.

Содержит:
1. Асинхронный движок подключения к SQLite.
2. Фабрику асинхронных сессий.
3. Проверку и инициализацию базы данных.
"""
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

from app.database.init_db import init_db

engine = create_async_engine(
    settings.DB_TIMETABLE_URL,                 # строка подключения к PostgreSQL
    echo=False,                                # echo=True = логировать SQL-запросы в консоль
    future=True,                               # новый API SQLAlchemy 2.0
    poolclass=StaticPool,                      # одно и то же соединение для всех операций
    connect_args={"check_same_thread": False}  # для работы в нескольких потоках
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False
)

async def startup():
    """Проверка существования бд и инициализация при отсутствии"""
    await init_db(engine)