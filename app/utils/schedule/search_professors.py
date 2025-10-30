import logging

from sqlalchemy import select
from rapidfuzz import process

from app.database.db import AsyncSessionLocal
from app.database.models import Professor


logger = logging.getLogger(__name__)


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

    Каждый вызов функции напрямую обращается к базе данных, без использования кэша.

    Параметры:
        query (str): Поисковый запрос пользователя
        limit (int): Максимальное количество результатов
        score_cutoff (float): Пороговое значение сходства (минимальное значение схожести)

    Возвращает:
        tuple[Professor | None, list[Professor]]:
            exact_match — объект Professor, если найдено точное совпадение;
            similar_professors — список похожих преподавателей.
    """

    if not query:
        return None, []

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Professor))
            all_professors = result.scalars().all()
    except Exception as e:
        logger.error("Ошибка при загрузке преподавателей: %s", e)
        return None, []

    if not all_professors:
        return None, []

    query_normalized = _normalize_name(query)

    professors_dict = {}

    for professor in all_professors:
        normalized = _normalize_name(professor.name)
        professors_dict[normalized] = professor

    matches = process.extract(
        query=query_normalized,            # что ищем
        choices=professors_dict.keys(),    # где ищем
        limit=limit,                       # максимальное количество результатов
        score_cutoff=score_cutoff          # минимальный порог сходства
    )

    exact_match = None
    similar_professors = []

    for normalized_name, score, _ in matches:
        professor = professors_dict[normalized_name]

        if normalized_name == query_normalized:
            exact_match = professor
        else:
            similar_professors.append(professor)

    return exact_match, similar_professors