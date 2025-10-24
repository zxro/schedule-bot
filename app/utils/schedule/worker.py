"""
Синхронизация расписания из внешнего API в базу данных.

Основные задачи:
1. Получить список групп с API.
2. Проверить и создать при необходимости факультеты и группы в базе данных.
3. Получить расписание для каждой группы.
4. Синхронизировать записи пар (удаление старых и вставка новых) в таблице Lesson.
5. Синхронизировать расписание для преподавателей
6. Вести логирование всех шагов, ошибок и количества обработанных групп.

Используемые компоненты:
- TimetableClient (app/fetcher.py): асинхронный клиент для API расписания.
- extract_lessons_from_timetable_json (app/parser.py): парсер JSON-расписания в список словарей.
- AsyncSessionLocal (app/db.py): фабрика асинхронных сессий SQLAlchemy.
- SQLAlchemy модели: Faculty, Group, Lesson, TimeSlot, WeekMarkEnum.
"""
import asyncio
import logging
from typing import List, Set

from app.keyboards.init_keyboards import refresh_all_keyboards
from app.utils.schedule.fetcher import TimetableClient
from app.utils.schedule.parser import extract_lessons_from_timetable_json, extract_professor_names
from app.database.db import AsyncSessionLocal
from app.database.models import Faculty, Group, Lesson, Professor, ProfessorLesson
from sqlalchemy import select, delete, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.schedule.search_professors import get_cached_professors

logger = logging.getLogger(__name__)


CACHE_UPDATE_ENABLED = True
_cache_lock = asyncio.Lock()


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

    logger.info("Удалена группа без расписания: %s", group_name)
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
            lesson = Lesson(
                group_id=group_obj.id,
                weekday=rec.get("weekday"),
                lesson_number=rec.get("lesson_number"),
                subject=rec.get("subject"),
                professors=rec.get("professors"),
                rooms=rec.get("rooms"),
                week_mark=rec.get("week_mark"),
                type=rec.get("type"),
            )
            session.add(lesson)
            count += 1

        return count

    except Exception as e:
        logger.error(f"Ошибка при обновлении пар для группы group_id = {group_obj.id}: {e}")
        await session.rollback()
        raise


async def upsert_lessons_for_professors(session: AsyncSession):
    """
    Полностью перестраивает расписание преподавателей
    на основе таблицы Lesson.

    Логика:
    1. Удаляет все старые записи в professor_lessons.
    2. Проходит по всем Lesson.
    3. Для каждого преподавателя в строке создаёт (или находит) Professor.
    4. Добавляет новые пары без дублей.
    """

    try:
        logger.info("🔄 Обновляется расписание преподавателей...")

        await session.execute(delete(ProfessorLesson))

        result = await session.execute(select(Lesson))
        lessons = result.scalars().all()

        professors_cache: dict[str, int] = {}  # имя -> id
        added_records: set[tuple[int, int, int, str, str, str]] = set()  # защита от дублей

        for lesson in lessons:
            professors_text = (lesson.professors or "").strip()
            if not professors_text:
                continue

            professor_names = extract_professor_names(professors_text)

            if not professor_names:
                continue

            for prof_name in professor_names:
                prof_id = professors_cache.get(prof_name)
                if not prof_id:
                    res = await session.execute(select(Professor).where(Professor.name == prof_name))
                    professor = res.scalar_one_or_none()
                    if not professor:
                        professor = Professor(name=prof_name)
                        session.add(professor)
                        await session.flush()
                    prof_id = professor.id
                    professors_cache[prof_name] = prof_id

                # проверка дублей
                key = (
                    prof_id,
                    lesson.weekday,
                    lesson.lesson_number,
                    lesson.subject,
                    lesson.rooms,
                    lesson.week_mark,
                )
                if key in added_records:
                    continue
                added_records.add(key)

                pl = ProfessorLesson(
                    professor_id=prof_id,
                    weekday=lesson.weekday,
                    lesson_number=lesson.lesson_number,
                    subject=lesson.subject,
                    rooms=lesson.rooms,
                    week_mark=lesson.week_mark,
                )
                session.add(pl)

        await session.flush()
        logger.info(f"✅ Расписание преподавателей успешно обновлено. Обработано {len(added_records)} записей.")

    except Exception as e:
        logger.error(f"Ошибка при перестроении расписания преподавателей: {e}")
        await session.rollback()
        raise


async def run_full_sync(limit_groups: int = None, type_idx: int = 0):
    """
    Полная синхронизация расписаний групп и преподавателей.

    1. Получает все группы из API.
    2. Для каждой группы:
       - создаёт факультет и группу, если их нет.
       - получает и парсит расписание.
       - обновляет таблицу Lesson.
    3. После обработки всех групп перестраивает расписание преподавателей.
    4. Удаляет неактуальные группы и преподавателей.
    5. Обновляет клавиатуры.
    """

    global CACHE_UPDATE_ENABLED

    client = TimetableClient()

    try:
        async with AsyncSessionLocal() as session:
            groups_json = await client.fetch_groups()
            groups = groups_json.get("groups", []) if isinstance(groups_json, dict) else groups_json

            if not groups:
                logger.warning("Список групп пуст.")
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
                    valid_groups.add(group_name)

                    await session.commit()
                    logger.info("Обработана группа %s → %d пар", group_name, inserted)

                except Exception as e:
                    await session.rollback()
                    logger.error("Ошибка при обработке группы %s: %s", group_name, str(e))
                    continue

            # Удаляем неактуальные группы с обработкой исключений
            deleted_groups = 0
            try:
                q = await session.execute(select(Group))
                existing_groups = q.scalars().all()
                for grp in existing_groups:
                    if grp.group_name not in valid_groups:
                        deleted_groups += 1
                        await session.execute(delete(Lesson).where(Lesson.group_id == grp.id))
                        await session.delete(grp)
                        logger.info("Удалена группа без расписания: %s", grp.group_name)

                await session.commit()

            except Exception as e:
                await session.rollback()
                logger.error("Ошибка при удалении групп: %s", str(e))

            async with _cache_lock:
                CACHE_UPDATE_ENABLED = False

            try:
                await upsert_lessons_for_professors(session)
                await session.commit()

                deleted_profs = 0
                try:
                    q = await session.execute(select(Professor))
                    existing_profs = q.scalars().all()
                    for prof in existing_profs:
                        res = await session.execute(
                            select(ProfessorLesson).where(ProfessorLesson.professor_id == prof.id)
                        )
                        lessons_for_prof = res.scalars().all()
                        if not lessons_for_prof:
                            deleted_profs += 1
                            await session.delete(prof)
                            logger.info("Удалён преподаватель без пар: %s", prof.name)

                    await session.commit()

                except Exception as e:
                    await session.rollback()
                    logger.error("Ошибка при удалении преподавателей: %s", str(e))

            except Exception as e:
                await session.rollback()
                logger.error("Ошибка при обновлении расписания преподавателей: %s", str(e))

            finally:
                async with _cache_lock:
                    CACHE_UPDATE_ENABLED = True

    except Exception as e:
        logger.error("Критическая ошибка в синхронизации: %s", str(e))
        raise

    finally:
        await client.close()

        await get_cached_professors()

    logger.info("✅ Полная синхронизация завершена.")
    logger.info("Групп с расписанием: %d (удалено: %d)", len(valid_groups), deleted_groups)
    logger.info("Преподавателей: %d, удалено: %d", len(existing_profs) - deleted_profs, deleted_profs)

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
        logger.info("✅ Синхронизация для %s завершена. Групп обработано: %d",
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


async def get_lesson_for_professor(professor_name: str):
    """Получить все пары преподавателя по имени"""
    async with AsyncSessionLocal() as session:
        query = await session.execute(
            select(Professor).where(Professor.name.ilike(f"%{professor_name}%"))
        )
        professors = query.scalars().all()

        if not professors or len(professors) > 1:
            return None, professors

        professor = professors[0]

        query = await session.execute(
            select(ProfessorLesson)
            .where(ProfessorLesson.professor_id == professor.id)
            .order_by(ProfessorLesson.weekday, ProfessorLesson.lesson_number)
        )
        lessons = query.scalars().all()

        return professor, lessons