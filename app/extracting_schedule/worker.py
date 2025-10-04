"""
Синхронизация расписания из внешнего API в базу данных.

Основные задачи:
1. Получить список групп с API.
2. Проверить и создать при необходимости факультеты и группы в базе данных.
3. Получить расписание для каждой группы.
4. Синхронизировать записи пар (удаление старых и вставка новых) в таблице Lesson.
5. Вести логирование всех шагов, ошибок и количества обработанных групп.

Используемые компоненты:
- TimetableClient (app/fetcher.py): асинхронный клиент для API расписания.
- extract_lessons_from_timetable_json (app/parser.py): парсер JSON-расписания в список словарей.
- AsyncSessionLocal (app/db.py): фабрика асинхронных сессий SQLAlchemy.
- SQLAlchemy модели: Faculty, Group, Lesson, TimeSlot, WeekMarkEnum.
"""

import logging
from typing import List

from app.extracting_schedule.fetcher import TimetableClient
from app.extracting_schedule.parser import extract_lessons_from_timetable_json
from app.database.dp import AsyncSessionLocal
from app.database.models import Faculty, Group, Lesson
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def ensure_faculty_and_group(session: AsyncSession, faculty_name: str, group_name: str):
    """
    Получает или создаёт факультет и группу в базе данных.

    Логика:
    - Если указан faculty_name, ищем факультет в базе, если нет — создаём.
    - Ищем группу по group_name, если нет — создаём и привязываем к факультету.
    - Используется await session.flush() чтобы получить id для связи с другими таблицами.

    Параметры:
        session (AsyncSession): асинхронная сессия SQLAlchemy.
        faculty_name (str): название факультета.
        group_name (str): название группы.

    Возвращает:
        Group: объект группы из базы данных.
    """

    faculty = None
    if faculty_name:
        q = await session.execute(select(Faculty).where(Faculty.name == faculty_name))
        faculty = q.scalars().first()
        if not faculty:
            faculty = Faculty(name=faculty_name)
            session.add(faculty)
            await session.flush()

    q = await session.execute(select(Group).where(Group.group_name == group_name))
    group = q.scalars().first()
    if not group:
        group = Group(group_name=group_name, faculty_id=faculty.id if faculty else None)
        session.add(group)
        await session.flush()
    return group


async def upsert_lessons_for_group(session: AsyncSession, group_obj: Group, records: List[dict]):
    """
    Обновляет расписание для конкретной группы.

    Логика:
    - Для упрощения сначала удаляются старое расписание для этой группы.
    - Вставляются новые записи из списка records.
    - week_mark конвертируется в допустимое перечисление (None, 'every', 'plus', 'minus').

    Параметры:
        session (AsyncSession): асинхронная сессия SQLAlchemy.
        group_obj (Group): объект группы.
        records (List[dict]): список словарей с информацией о парах.

    Возвращает:
        int: количество вставленных пар.
    """
    if not records:
        return 0

    type_name = records[0].get("type")

    await session.execute(
        delete(Lesson)
        .where(Lesson.group_id == group_obj.id)
        .where(Lesson.type == type_name)
    )
    await session.flush()

    count = 0
    for rec in records:
        wm = rec.get("week_mark") or None
        if wm not in (None, "every", "plus", "minus"):
            wm = None

        lesson = Lesson(
            group_id=group_obj.id,
            date=rec.get("date"),
            weekday=rec.get("weekday"),
            lesson_number=rec.get("lesson_number"),
            start_time=rec.get("start_time"),
            end_time=rec.get("end_time"),
            subject=rec.get("subject"),
            professors=rec.get("professors"),
            rooms=rec.get("rooms"),
            week_mark=wm,
            type=rec.get("type"),
            raw_json=rec.get("raw")
        )
        session.add(lesson)
        count += 1
    return count


async def run_full_sync(limit_groups: int = None, type_idx: int = 0):
    """
    Основная функция синхронизации расписания.

    Логика работы:
    1. Создаём клиент TimetableClient для API.
    2. Получаем список всех групп.
    3. Для каждой группы:
        - проверяем и создаём факультет и группу в базе
        - получаем расписание с API
        - пропускаем группы без расписания (message "not found")
        - парсим пары в список словарей
        - обновляем записи пар через upsert_lessons_for_group
        - коммитим изменения и ведём лог.
    4. Закрываем клиент API.
    5. Логируем количество обработанных групп.

    Параметры:
        limit_groups (int, optional): ограничение числа групп для обработки (для тестов). None — все.
        type_idx (int, optional): тип расписания для запроса (по умолчанию 0).

    Возвращает:
        None
    """

    client = TimetableClient()
    async with AsyncSessionLocal() as session:
        groups_json = await client.fetch_groups()
        groups = groups_json.get("groups", []) if isinstance(groups_json, dict) else groups_json

        if not groups:
            logger.warning("Список групп пуст")
            await client.close()
            return

        total = 0
        for idx, g in enumerate(groups):
            if limit_groups and idx >= limit_groups:
                break
            group_name = g.get("groupName")
            faculty_name = g.get("facultyName")
            if not group_name:
                continue
            try:
                group_obj = await ensure_faculty_and_group(session, faculty_name, group_name)

                tt_json = await client.fetch_timetable_for_group(group_name, type_idx=type_idx)

                if isinstance(tt_json, dict) and tt_json.get("message"):
                    logger.info("Нет расписания для %s: %s", group_name, tt_json.get("message"))
                    continue

                records = extract_lessons_from_timetable_json(group_name, tt_json)

                inserted = await upsert_lessons_for_group(session, group_obj, records)
                await session.commit()
                total += 1
                logger.info("Обработана группа %s -> вставлено %d пар", group_name, inserted)
            except Exception as e:
                logger.error("Ошибка при обработке группы %s: %s", group_name, e)
                await session.rollback()

        await client.close()

    logger.info("Синхронизация завершена. Групп обработано: %d", total)

async def run_full_sync_for_group(group_name: str, type_idx: int = 0):
    """
    Полная синхронизация расписания для одной группы.

        Параметры:
        group_name : str
            Название группы, для которой выполняется синхронизация.
        type_idx : int, optional (default=0)
            Индекс типа расписания (например, лекции/практики), используется при получении JSON.

        Возвращает:
        int
            Количество вставленных/обновленных записей расписания.
            Если API возвращает сообщение об ошибке, возвращает 0.

        Логика работы функции:
        1. Создаем клиент `TimetableClient` для получения расписания.
        2. Открываем асинхронную сессию базы данных (`AsyncSessionLocal`).
        3. В блоке try/finally:
            a. Убедимся, что факультет и группа существуют в БД через `ensure_faculty_and_group`.
            b. Получаем JSON расписания через `client.fetch_timetable_for_group(group_name, type_idx)`.
            c. Если API вернул словарь с ключом "message" — считаем, что данных нет и возвращаем 0.
            d. Преобразуем JSON в список записей через `extract_lessons_from_timetable_json`.
            e. Вставляем или обновляем уроки в БД через `upsert_lessons_for_group`.
            f. Фиксируем изменения с помощью `session.commit()`.
            g. Возвращаем количество вставленных/обновленных уроков.
        4. В блоке finally закрываем клиента `TimetableClient`.
        """
    client = TimetableClient()
    async with AsyncSessionLocal() as session:
        try:
            group_obj = await ensure_faculty_and_group(session, None, group_name)

            tt_json = await client.fetch_timetable_for_group(group_name, type_idx)
            if isinstance(tt_json, dict) and tt_json.get("message"):
                return 0

            records = extract_lessons_from_timetable_json(group_name, tt_json)
            inserted = await upsert_lessons_for_group(session, group_obj, records)

            await session.commit()
            return inserted
        finally:
            await client.close()

async def get_schedule_for_group(group_name: str):
    """
    Получение расписания группы из базы данных.

    Параметры:
    ----------
    group_name : str
        Название группы, для которой нужно получить расписание.

    Возвращает:
    ----------
    List[Lesson]
        Список объектов Lesson, принадлежащих указанной группе.
        Если группа не найдена — возвращает пустой список.

    Логика работы функции:
    --------------------
    1. Создаем асинхронную сессию с базой данных.
    2. Выполняем запрос к таблице `Group`, фильтруя по `group_name`.
    3. Если группа не найдена, возвращаем пустой список.
    4. Если группа найдена:
        a. Выполняем запрос к таблице `Lesson`, выбирая пары с `group_id` соответствующей группы.
        b. Возвращаем все найденные пары.
    """

    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Group).where(Group.group_name == group_name))
        group = q.scalars().first()
        if not group:
            return []

        q = await session.execute(select(Lesson).where(Lesson.group_id == group.id))
        lessons = q.scalars().all()
        return lessons