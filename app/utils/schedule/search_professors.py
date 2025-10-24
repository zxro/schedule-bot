from sqlalchemy import select
from rapidfuzz import process
from typing import List, Tuple
import asyncio


from app.database.db import AsyncSessionLocal
from app.database.models import Professor


# Глобальный кэш для преподавателей
_professors_cache: List[Tuple[Professor, str]] = None
_cache_lock = asyncio.Lock()
_cache_timestamp = 0
CACHE_TTL = 300  # 5 минут


async def get_cached_professors() -> List[Tuple[Professor, str]]:
    """
    Получает список преподавателей с нормализованными именами из кэша или базы.
    """
    global _professors_cache, _cache_timestamp

    current_time = asyncio.get_event_loop().time()

    # Если кэш пустой или устарел, обновляем его
    if _professors_cache is None or (current_time - _cache_timestamp) > CACHE_TTL:
        async with _cache_lock: # Проверка под блокировкой
            if _professors_cache is None or (current_time - _cache_timestamp) > CACHE_TTL:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(Professor))
                    all_professors = result.scalars().all()

                # Нормализуем имена один раз и сохраняем в кэш
                _professors_cache = [
                    (prof, _normalize_name(prof.name))
                    for prof in all_professors
                ]
                _cache_timestamp = current_time

    return _professors_cache

async def invalidate_professors_cache():
    """
    Сброс кэша преподавателей.
    """
    global _professors_cache, _cache_timestamp
    async with _cache_lock:
        _professors_cache = None
        _cache_timestamp = 0

def _normalize_name(name: str) -> str:
    """Нормализация — убираем лишние точки и двойные пробелы и заменяем 'ё' на 'е'."""
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
        # print(f"normalized_name: {normalized_name}, score: {score}")
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