from sqlalchemy import select
from rapidfuzz import process

from app.database.db import AsyncSessionLocal
from app.database.models import Professor


async def search_professors_fuzzy(query: str, limit: int = 10) -> list[Professor]:
    """
    Поиск преподавателей с использованием нечеткого сравнения RapidFuzz.

    Параметры:
        query (str): Поисковый запрос пользователя
        limit (int): Максимальное количество результатов

    Возвращает:
        list[Professor]: Список найденных преподавателей
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Professor))
        all_professors = result.scalars().all()

    if not all_professors:
        return []

    query_lower = query.lower()
    professor_names_lower = [prof.name.lower() for prof in all_professors]

    matches = process.extract(
        query_lower,          # что ищем
        professor_names_lower,      # где ищем
        limit=limit,          # максимальное количество результатов
        score_cutoff=78.5     # минимальный порог
    )

    matched_professors = []
    for name_lower, score, _ in matches:
        professor = next((prof for prof in all_professors if prof.name.lower() == name_lower), None)
        if professor:
            matched_professors.append(professor)

    return matched_professors


async def get_exact_professor_match(query: str) -> Professor | None:
    """
    Поиск точного совпадения преподавателя.

    Параметры:
        query (str): Поисковый запрос пользователя

    Возвращает:
        Professor | None: Найденный преподаватель или None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Professor).where(Professor.name.ilike(f"%{query}%"))
        )
        professors = result.scalars().all()

    if not professors:
        return None

    # Точное совпадение
    query_lower = query.lower().strip()
    for professor in professors:
        if professor.name.lower().strip() == query_lower:
            return professor

    return None