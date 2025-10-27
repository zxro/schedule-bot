"""
Парсер JSON ответа timetable -> объекты, пригодные для записи в БД.
"""
import re
from datetime import time
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def extract_professor_names(professors_text: str) -> list[str]:
    """
    Извлекает имена преподавателей из текста, убирая должности в скобках.
    """

    if not professors_text:
        return []

    def remove_unbalanced_brackets(text: str):
        """Удаляет несбалансированные скобки"""
        result = []
        stack = []

        for char in text:
            if char == '(':
                stack.append(len(result))
                result.append(char)
            elif char == ')':
                if stack:
                    stack.pop()
                    result.append(char)
            else:
                result.append(char)

        for pos in reversed(stack):
            del result[pos]

        return ''.join(result)

    # Убираем должности в скобках
    cleaned_text = re.sub(r'\([^)]*\)', '', professors_text)
    # Убираем точки у инициалов
    cleaned_text = re.sub(r'\.', ' ', cleaned_text)
    # Убираем несбалансированные скобки
    cleaned_text = remove_unbalanced_brackets(cleaned_text)
    # Убираем лишние пробелы
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text.strip())

    names = [name.strip() for name in cleaned_text.split(',') if name.strip()]

    return names


def parse_lesson_time_data(lesson_time_data: List[Dict[str, str]]) -> Dict[int, Dict[str, time]]:
    """
    Преобразует список данных о времени пар из JSON в словарь с объектами времени.

    Параметры:
    lesson_time_data : List[Dict[str, str]]
        Список словарей, каждый из которых содержит ключи:
        - "start": строка времени начала пары в формате "HH:MM"
        - "end": строка времени окончания пары в формате "HH:MM"

    Возвращает:
    Dict[int, Dict[str, time]]
        Словарь, где ключ — номер пары (начиная с 1),
        значение — словарь с ключами "start" и "end", содержащими объекты datetime.time.

    Логика работы:
    1. Создается пустой словарь lesson_time_map.
    2. Проходим по списку lesson_time_data, нумерация начинается с 1.
    3. Для каждого элемента lt:
        a. Преобразуем lt["start"] в объект time с помощью time.fromisoformat.
        b. Преобразуем lt["end"] аналогично.
        c. Сохраняем результат в lesson_time_map[idx] = {"start": start, "end": end}.
    4. Если при парсинге возникает ошибка, логируем ее через logger.error.
    5. Возвращаем lesson_time_map.
    """

    lesson_time_map = {}
    for idx, lt in enumerate(lesson_time_data, start=0):
        try:
            start = time.fromisoformat(lt["start"])
            end = time.fromisoformat(lt["end"])
            lesson_time_map[idx] = {"start": start, "end": end}
        except Exception as e:
            logger.error("Ошибка извлечения времени пары: %s", e)

    return lesson_time_map


def extract_lessons_from_timetable_json(group_name: str, timetable_json: Dict[str, Any]):
    """
    Извлекает список пар из JSON расписания, приводя его к форме,
    пригодной для записи в базу данных.

    Параметры:
    group_name : str
        Название группы, для которой обрабатывается расписание.
    timetable_json : Dict[str, Any]
        JSON-объект расписания, может содержать:
        - "lessonTimeData": список с временем пар
        - "lessonsContainers" или "lessons": список контейнеров уроков
        - "types" / "type" / "typesName": тип занятий (лекция, практика и т.д.)

    Возвращает:
    List[Dict[str, Any]]
        Список словарей, каждый из которых описывает одна пара:
        {
            "group_name": str,
            "weekday": int | None,
            "lesson_number": int | None,
            "subject": str | None,
            "professors": str | None,
            "rooms": str | None,
            "week_mark": str | None,
            "type": str,
        }

    Логика работы:
    1. Если timetable_json пустой, возвращаем пустой список.
    2. Приводим timetable_json к списку timetables.
    3. Создаем множество seen_lessons для уникальности пар.
    4. Для каждого расписания tt в timetables:
        a. Если есть "lessonTimeData", вызываем parse_lesson_time_data для получения словаря lesson_time_map.
        b. Определяем тип занятия ttype, проверяя несколько возможных ключей.
        c. Получаем список контейнеров пар containers.
    5. Для каждого контейнера cont:
        a. Определяем lesson_number и weekday.
        b. Получаем week_mark.
        c. Из списка texts извлекаем subject, professors, rooms.
        d. Формируем ключ урока lesson_key для проверки уникальности.
        e. Если lesson_key уже встречался, пропускаем текущую пару.
        f. Создаем словарь rec с данными пары и добавляем его в records.
    6. Возвращаем список records.
    """

    records = []
    if not timetable_json:
        return records

    timetables = timetable_json if isinstance(timetable_json, list) else [timetable_json]

    seen_lessons = set()

    for tt in timetables:
        lesson_time_map = {}
        if "lessonTimeData" in tt and isinstance(tt["lessonTimeData"], list):
            lesson_time_map = parse_lesson_time_data(tt["lessonTimeData"])

        ttype = tt.get("types") or tt.get("type") or tt.get("typesName") or "classes"
        containers = tt.get("lessonsContainers") or tt.get("lessons") or []

        for cont in containers:
            lesson_number = cont.get("lessonNumber") if cont.get("lessonNumber") is not None else None
            weekday = cont.get("weekDay") or cont.get("week_day")
            week_mark = cont.get("weekMark")

            texts = cont.get("texts") or []
            subject = texts[1] if len(texts) > 1 else None
            professors = texts[2] if len(texts) > 2 else None
            rooms = texts[3] if len(texts) > 3 else None

            start_time = lesson_time_map.get(lesson_number, {}).get("start")
            end_time = lesson_time_map.get(lesson_number, {}).get("end")

            lesson_key = (
                weekday,
                lesson_number,
                subject,
                professors,
                rooms,
                week_mark,
                ttype,
                start_time,
                end_time
            )

            if lesson_key in seen_lessons:
                continue
            seen_lessons.add(lesson_key)

            rec = {
                "group_name": group_name,
                "weekday": weekday,
                "lesson_number": lesson_number,
                "subject": subject,
                "professors": professors,
                "rooms": rooms,
                "week_mark": week_mark,
                "type": ttype,
            }

            records.append(rec)

    return records