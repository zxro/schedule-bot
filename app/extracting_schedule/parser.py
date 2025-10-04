"""
Парсер JSON ответа timetable -> объекты, пригодные для записи в БД.
"""
from datetime import time, datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

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
    for idx, lt in enumerate(lesson_time_data, start=1):
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
            "date": date | None,
            "weekday": int | None,
            "lesson_number": int | None,
            "start_time": time | None,
            "end_time": time | None,
            "subject": str | None,
            "professors": str | None,
            "rooms": str | None,
            "week_mark": str | None,
            "type": str,
            "raw": dict (оригинальный контейнер)
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
        d. Определяем start_time и end_time через lesson_time_map.
        e. Если есть поле date, пытаемся преобразовать его в объект datetime.date.
        f. Формируем ключ урока lesson_key для проверки уникальности.
        g. Если lesson_key уже встречался, пропускаем текущую пару.
        h. Создаем словарь rec с данными пары и добавляем его в records.
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
            lesson_number = cont.get("lessonNumber") + 1 if cont.get("lessonNumber") is not None else None
            weekday = cont.get("weekDay") or cont.get("week_day")
            week_mark = cont.get("weekMark")

            texts = cont.get("texts") or []
            subject = texts[1] if len(texts) > 1 else None
            professors = texts[2] if len(texts) > 2 else None
            rooms = texts[3] if len(texts) > 3 else None

            start_time = lesson_time_map.get(lesson_number, {}).get("start")
            end_time = lesson_time_map.get(lesson_number, {}).get("end")

            date_str = cont.get("date")
            date_obj = None
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
                except Exception:
                    logger.error("Не удалось извлечь дату %s", date_str)
                    pass

            lesson_key = (weekday, lesson_number, subject, professors, rooms, week_mark, ttype)

            if lesson_key in seen_lessons:
                continue
            seen_lessons.add(lesson_key)

            rec = {
                "group_name": group_name,
                "date": date_obj,
                "weekday": weekday,
                "lesson_number": lesson_number,
                "start_time": start_time,
                "end_time": end_time,
                "subject": subject,
                "professors": professors,
                "rooms": rooms,
                "week_mark": week_mark,
                "type": ttype,
                "raw": cont
            }

            records.append(rec)

    return records