import logging

from sqlalchemy import select
from rapidfuzz import process
from typing import List, Tuple
import asyncio

from app.database.db import AsyncSessionLocal
from app.database.models import Professor
import app.utils.schedule.worker as worker


logger = logging.getLogger(__name__)


_professors_cache: List[Tuple[Professor, str]] = []
"""
Кэш преподавателей в формате списка кортежей (Professor, normalized_name).
Содержит пары: объект преподавателя и его нормализованное имя для быстрого поиска.
Инициализируется пустым списком при запуске бота.
"""

_cache_lock = asyncio.Lock()
"""
Асинхронная блокировка для защиты кэша от race conditions.
Гарантирует, что только одна корутина может обновлять кэш одновременно.
Используется в сочетании с double-checked locking pattern.
"""


async def get_cached_professors() -> List[Tuple[Professor, str]]:
    """
    Получает актуальный кэш преподавателей.

    Реализует паттерн double-checked locking для эффективного кэширования:
    - Проверяет флаг CACHE_UPDATE_ENABLED для принудительного управления обновлениями
    - Автоматически обновляет кэш только при первом запросе (инициализация)
    - Защищает от race conditions с помощью асинхронной блокировки

    Возвращает:
        List[Tuple[Professor, str]]: Список кортежей (преподаватель, нормализованное_имя)

    Исключения:
        OperationalError: При проблемах с подключением к базе данных
        Exception: При других непредвиденных ошибках во время обновления кэша
    """

    global _professors_cache

    if not worker.CACHE_UPDATE_ENABLED:
        return _professors_cache

    # Обновляем кэш только если он пустой (инициализация)
    if not _professors_cache:
        async with _cache_lock:
            # Вторая проверка под блокировкой
            if not _professors_cache:
                await _update_professors_cache()

    return _professors_cache


async def update_professors_cache() -> None:
    """
    Принудительное обновление кэша преподавателей.

    Используется для ручного обновления кэша после изменений в данных,
    таких как завершение полной синхронизации.

    Исключения:
        OperationalError: При проблемах с подключением к базе данных
        Exception: При других непредвиденных ошибках во время обновления кэша
    """

    global _professors_cache

    async with _cache_lock:
        await _update_professors_cache()


async def _update_professors_cache() -> None:
    """
    Внутренняя функция для обновления кэша преподавателей.

    Выполняет непосредственную загрузку данных из базы и обновление кэша.
    Должна вызываться только под блокировкой _cache_lock.
    """

    global _professors_cache

    if not worker.CACHE_UPDATE_ENABLED:
        return

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Professor))
            all_professors = result.scalars().all()

        _professors_cache = [
            (prof, _normalize_name(prof.name))
            for prof in all_professors
        ]

        logger.info("✅ Кэш преподавателей обновлён. Загружено %d преподавателей", len(_professors_cache))

    except Exception as e:
        logger.error("Ошибка при обновлении кэша преподавателей: %s", str(e))
        raise


async def invalidate_professors_cache():
    """
    Принудительно сбрасывает кэш преподавателей.

    Используется в следующих сценариях:
    - После синхронизации расписания для обеспечения актуальности данных
    - При ручном обновлении данных администратором
    - При обнаружении неконсистентности данных

    Операция защищена блокировкой для thread-safety.
    Сбрасывает кэш и временную метку, принуждая следующему запросу
    выполнить полное обновление из базы данных.
    """

    global _professors_cache
    async with _cache_lock:
        _professors_cache = []
        _cache_timestamp = 0


def _normalize_name(name: str) -> str:
    """
    Нормализует имя преподавателя для унифицированного поиска.

    Выполняет следующие преобразования:
    - Приведение к нижнему регистру
    - Замена точек на пробелы (для инициалов)
    - Замена буквы 'ё' на 'е'
    - Удаление лишних пробелов и пробелов по краям

    Args:
        name (str): Исходное имя преподавателя в любом регистре

    Возвращает:
        str: Нормализованное имя в нижнем регистре без лишних пробелов
    """

    if not name:
        return ""

    s = name.lower()
    s = s.replace(".", " ").replace("ё", "е")
    s = " ".join(s.split())

    return s.strip()


async def search_professors_fuzzy(query: str, limit: int = 10, score_cutoff: float = 80.0) -> tuple[Professor | None, list[Professor]]:
    """
    Поиск преподавателей с использованием нечеткого сравнения RapidFuzz.

    Параметры:
        query (str): Поисковый запрос пользователя
        limit (int): Максимальное количество результатов
        score_cutoff (float): Пороговое значения оценки (минимальное сходство)

    Возвращает:
        list[Professor]: Список найденных преподавателей
    """

    professors_normalized = await get_cached_professors()

    if not professors_normalized:
        return None, []

    query_normalized = _normalize_name(query)
    professor_names_normalized = [normalized for _, normalized in professors_normalized]

    matches = process.extract(
        query=query_normalized,               # что ищем
        choices=professor_names_normalized,   # где ищем
        limit=limit,                          # максимальное количество результатов
        score_cutoff=score_cutoff             # минимальный порог сходства
    )

    exact_match = None
    similar_professors = []

    for normalized_name, score, _ in matches:
        professor = next(
            (prof for prof, norm_name in professors_normalized
             if norm_name == normalized_name),
            None
        ) # сопоставление имён из результатов поиска с объектами из базы данных

        if professor:
            if normalized_name == query_normalized:
                exact_match = professor
            else:
                similar_professors.append(professor)

    return exact_match, similar_professors