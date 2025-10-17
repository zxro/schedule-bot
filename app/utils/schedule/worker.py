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
from typing import List, Set

from app.keyboards.init_keyboards import refresh_all_keyboards
from app.utils.schedule.fetcher import TimetableClient
from app.utils.schedule.parser import extract_lessons_from_timetable_json
from app.database.db import AsyncSessionLocal
from app.database.models import Faculty, Group, Lesson
from sqlalchemy import select, delete, case
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


async def delete_group_if_exists(session, group_name: str):
    """
    Удаляет группу и все связанные с ней пары, если она существует в БД.

    Параметры:
        session (AsyncSession): активная сессия SQLAlchemy.
        group_name (str): название группы, которую нужно удалить.

    Логика:
    1. Проверяет наличие группы по имени.
    2. Если группа найдена — удаляет все записи Lesson, связанные с ней.
    3. Удаляет саму группу.
    4. Фиксирует изменения через commit().
    """

    q = await session.execute(select(Group).where(Group.group_name == group_name))
    group = q.scalars().first()
    if not group:
        return False

    logger.info("Удаление группы %s — отсутствует расписание", group_name)
    await session.execute(delete(Lesson).where(Lesson.group_id == group.id))
    await session.delete(group)
    await session.commit()
    return True


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

    try:
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
                weekday=rec.get("weekday"),
                lesson_number=rec.get("lesson_number"),
                subject=rec.get("subject"),
                professors=rec.get("professors"),
                rooms=rec.get("rooms"),
                week_mark=wm,
                type=rec.get("type"),
            )
            session.add(lesson)
            count += 1

        return count

    except Exception as e:
        logger.error(f"Ошибка при обновлении пар для группы group_id = {group_obj.id}: {e}")
        await session.rollback()
        raise


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

        valid_groups: Set[str] = set()

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
                if not records:
                    logger.info("Для группы %s нет расписания", group_name)
                    continue

                inserted = await upsert_lessons_for_group(session, group_obj, records)
                await session.commit()

                valid_groups.add(group_name)
                logger.info("Обработана группа %s → вставлено %d пар", group_name, inserted)

            except Exception as e:
                await session.rollback()
                raise RuntimeError(
                    f"Факультет: {faculty_name}, Группа: {group_name}, Ошибка: {str(e)}"
                )

        deleted = 0
        q = await session.execute(select(Group))
        existing_groups = q.scalars().all()
        for grp in existing_groups:
            if grp.group_name not in valid_groups:
                deleted += 1
                logger.info("Удаление группы без расписания: %s", grp.group_name)
                await session.execute(delete(Lesson).where(Lesson.group_id == grp.id))
                await session.delete(grp)

        await session.commit()
        await client.close()

    logger.info("Полная синхронизация завершена. Групп с расписанием: %d. Удалено групп: %d",
                len(valid_groups), deleted)

    await refresh_all_keyboards()


async def run_full_sync_for_faculty(faculty_name: str, limit_groups: int = None, type_idx: int = 0):
    """
    Синхронизация расписания для всех групп определенного факультета.

    Логика работы:
    1. Получает список всех групп из API
    2. Фильтрует группы по указанному факультету
    3. Для каждой группы факультета:
        - Создает/проверяет запись группы в БД
        - Загружает расписание через API
        - Парсит и сохраняет данные в БД

    Параметры:
        faculty_name (str): Название факультета для синхронизации
        limit_groups (int, optional): Ограничение количества групп для обработки
        type_idx (int, optional): Тип расписания (по умолчанию 0)

    Возвращает:
        int: Количество обработанных групп
    """
    client = TimetableClient()
    async with AsyncSessionLocal() as session:
        groups_json = await client.fetch_groups()
        groups = groups_json.get("groups", []) if isinstance(groups_json, dict) else groups_json

        if not groups:
            logger.warning("Список групп пуст")
            await client.close()
            return 0

        faculty_groups = [g for g in groups if g.get("facultyName") == faculty_name]

        if not faculty_groups:
            logger.warning("Не найдено групп для факультета %s", faculty_name)
            await client.close()
            return 0

        valid_groups: Set[str] = set()
        for idx, g in enumerate(faculty_groups):
            if limit_groups and idx >= limit_groups:
                break

            group_name = g.get("groupName")
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

                valid_groups.add(group_name)
                logger.info("Обработана группа %s факультета %s -> вставлено %d пар",
                            group_name, faculty_name, inserted)

            except Exception as e:
                logger.error("Ошибка при обработке группы %s факультета %s: %s",
                             group_name, faculty_name, e)
                await session.rollback()

            qf = await session.execute(select(Faculty).where(Faculty.name == faculty_name))
            faculty_obj = qf.scalars().first()

        q = await session.execute(select(Group).where(Group.faculty_id == faculty_obj.id))
        existing = q.scalars().all()
        for g in existing:
            if g.group_name not in valid_groups:
                logger.info("Удаление группы без расписания: %s", g.group_name)
                await session.execute(delete(Lesson).where(Lesson.group_id == g.id))
                await session.delete(g)

        await session.commit()
        await client.close()

        total = len(valid_groups)
        logger.info("Синхронизация для %s завершена. Групп обработано: %d",
                    faculty_name, total)

        await refresh_all_keyboards()

        return total

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
            e. Вставляем или обновляем пары в БД через `upsert_lessons_for_group`.
            f. Фиксируем изменения с помощью `session.commit()`.
            g. Возвращаем количество вставленных/обновленных пар.
        4. В блоке finally закрываем клиента `TimetableClient`.
        """
    client = TimetableClient()
    async with AsyncSessionLocal() as session:
        try:
            groups_data = await client.fetch_groups()
            group_info = next(
                (g for g in groups_data.get("groups", []) if g["groupName"] == group_name),
                None
            )
            if not group_info:
                await delete_group_if_exists(session, group_name)
                return 0

            faculty_name = group_info["facultyName"]

            group_obj = await ensure_faculty_and_group(session, faculty_name, group_name)

            tt_json = await client.fetch_timetable_for_group(group_name, type_idx)
            if isinstance(tt_json, dict) and tt_json.get("message"):
                await delete_group_if_exists(session, group_name)
                return 0

            records = extract_lessons_from_timetable_json(group_name, tt_json)
            if not records:
                await delete_group_if_exists(session, group_name)
                return 0

            inserted = await upsert_lessons_for_group(session, group_obj, records)
            await session.commit()

            await refresh_all_keyboards()
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

        week_mark_order = case(
            (Lesson.week_mark == 'every', 1),
            (Lesson.week_mark == 'plus', 2),
            (Lesson.week_mark == 'minus', 3),
            else_=4
        )

        q = await session.execute(
            select(Lesson)
            .where(Lesson.group_id == group.id)
            .order_by(week_mark_order)
        )
        lessons = q.scalars().all()
        return lessons