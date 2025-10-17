"""
Формирование базовых inline-клавиатур для выбора факультетов и групп.

Модуль загружает данные о факультетах и группах из внешнего API
(settings.TIMETABLE_API_BASE + "/groups") и формирует базовые клавиатуры без кнопок отмены.

Назначение:
    - create_faculty_keyboard() — возвращает клавиатуру со списком факультетов.
    - create_courses_keyboards() — возвращает словарь клавиатур со списками групп по факультетам.

Использование:
    Эти функции служат базой для дальнейшего расширения:
    - В модулях синхронизации (`*_sync`) или поиска (`*_find`) к базовым клавиатурам добавляются
      кнопки отмены с разным callback_data.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import logging

from app.database.db import AsyncSessionLocal
from app.database.models import Faculty, Group
from app.utils.schedule.fetcher import TimetableClient

logger = logging.getLogger(__name__)

faculty_abbr = {
    "Математический факультет": "MATH",
    "Факультет прикладной математики и кибернетики": "PMIK",
    "Физико-технический факультет": "FTECH",
    "Химико-технологический факультет": "CHEM",
    "Аспирантура": "ASP",
    "Факультет географии и геоэкологии": "GEO",
    "Биологический факультет": "BIO",
    "Факультет психологии": "PSY",
    "Институт экономики и управления": "ECON",
    "Институт педагогического образования и социальных технологий": "PED",
    "Юридический факультет": "LAW",
    "Филологический факультет": "PHIL",
    "Факультет иностранных языков и международной коммуникации": "LANG",
    "Исторический факультет": "HIST",
    "Факультет физической культуры": "SPORT",
}

abbr_faculty = {
    "MATH": "Математический факультет",
    "PMIK": "Факультет прикладной математики и кибернетики",
    "FTECH": "Физико-технический факультет",
    "CHEM": "Химико-технологический факультет",
    "ASP": "Аспирантура",
    "GEO": "Факультет географии и геоэкологии",
    "BIO": "Биологический факультет",
    "PSY": "Факультет психологии",
    "ECON": "Институт экономики и управления",
    "PED": "Институт педагогического образования и социальных технологий",
    "LAW": "Юридический факультет",
    "PHIL": "Филологический факультет",
    "LANG": "Факультет иностранных языков и международной коммуникации",
    "HIST": "Исторический факультет",
    "SPORT": "Факультет физической культуры",
}

faculty_keyboard_base = None
groups_keyboards_base = None

async def refresh_base_keyboards():
    """
    Пересоздаёт базовые клавиатуры факультетов и групп.

    Логика:
        - Сначала пробует загрузить из БД.
        - Если данных нет, обращается к API.
        - Формирует глобальные переменные: faculty_keyboard_base и courses_keyboards_base.

    Возвращает:
        tuple[InlineKeyboardMarkup | None, dict[str, InlineKeyboardMarkup] | None]
    """
    global faculty_keyboard_base, groups_keyboards_base
    faculty_keyboard_base = await create_faculty_keyboard()
    groups_keyboards_base = await create_courses_keyboards()

def build_faculty_keyboards(faculty_groups: dict[str, list[str]]) -> dict[str, InlineKeyboardMarkup]:
    """
    Формирует клавиатуры для факультетов по спискам групп.

    Аргументы:
        faculty_groups: dict[str, list[str]] — {faculty_name: [group_name,...]}

    Возвращает:
        dict[str, InlineKeyboardMarkup] — {faculty_name: InlineKeyboardMarkup}
    """
    keyboards: dict[str, InlineKeyboardMarkup] = {}

    for faculty_name, group_names in faculty_groups.items():
        group_names.sort()
        keyboard, row = [], []
        for i, group_name in enumerate(group_names):
            row.append(InlineKeyboardButton(text=group_name, callback_data=f"group:{group_name}"))
            if len(row) == 3 or i == len(group_names) - 1:
                keyboard.append(row)
                row = []
        keyboards[faculty_name] = InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboards

# ================= ЗАГРУЗКА ДАННЫХ =================

async def load_groups_data():
    """
    Загружает данные групп из внешнего API через TimetableClient.

    Возвращает:
        dict: JSON-ответ от сервера (обычно содержит ключ 'groups'), если успешно.
        None: при ошибке (логируется).
    """
    client = TimetableClient()
    try:
        data = await client.fetch_groups()
        return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из API: {e}")
        return None
    finally:
        await client.close()


# ================= ФАКУЛЬТЕТЫ =================

async def create_faculty_keyboard():
    """
    Создаёт клавиатуру факультетов (предпочтительно из БД, иначе из API).

    Логика:
        - Загружает список групп через load_groups_data().
        - Извлекает уникальные факультеты.
        - Для каждого факультета создаёт кнопку с callback_data вида "faculty:<ABBR>".

    Возвращает:
        InlineKeyboardMarkup | None:
            - InlineKeyboardMarkup — клавиатура со списком факультетов.
            - None — если данные недоступны или не удалось создать клавиатуру.
    """

    # --- 1. Пробуем из БД ---
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Faculty.name).order_by(Faculty.name))
        faculties = q.scalars().all()

    if faculties:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f, callback_data=f"faculty:{faculty_abbr.get(f, f)}")]
                for f in faculties
            ]
        )

    # --- 2. Загрузка по API ---
    data = await load_groups_data()
    if not data or "groups" not in data:
        logger.warning("Не удалось получить список факультетов ни из БД, ни из API.")
        return None

    faculties = sorted(set(group['facultyName'] for group in data['groups']))
    keyboard = []
    for faculty in faculties:
        abbr = faculty_abbr.get(faculty)
        if not abbr:
            logger.warning("Факультет '%s' не найден в faculty_abbr.", faculty)
            continue
        keyboard.append([InlineKeyboardButton(text=faculty, callback_data=f"faculty:{abbr}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ================= ГРУППЫ =================

async def create_courses_keyboards():
    """
    Создаёт словарь клавиатур для групп факультетов (без кнопки отмены).

    Источник данных:
        1. Основной — база данных (таблицы Faculty и Group).
        2. Резервный — внешнее API (settings.TIMETABLE_API_BASE + "/groups").

    Логика:
        1. Пробует загрузить группы из БД (через ORM).
        2. Если в БД нет групп — делает запрос к API.
        3. Группирует группы по факультетам.
        4. Формирует клавиатуры, где группы расположены по 3 кнопки в ряд.

    Возвращает:
        dict[str, InlineKeyboardMarkup] | None:
            - {faculty_name: InlineKeyboardMarkup} — клавиатуры для факультетов.
            - None — если данные недоступны.
    """

    # ---------- 1. Попытка получить группы из БД ----------
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            select(Group)
            .options(selectinload(Group.faculty))
            .order_by(Group.group_name)
        )
        groups = q.scalars().all()

    faculty_groups: dict[str, list[str]] = {}
    for g in groups:
        if not g.faculty:
            continue
        faculty_groups.setdefault(g.faculty.name, []).append(g.group_name)

    if faculty_groups:
        return build_faculty_keyboards(faculty_groups)

    # ---------- 2. Если в БД нет групп, обращаемся к API ----------
    logger.warning("Не удалось получить группы из БД. Загружаем из API...")

    client = TimetableClient()
    try:
        data = await client.fetch_groups()
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных из API: {e}")
        await client.close()
        return None

    await client.close()

    if not data or "groups" not in data:
        logger.error("Некорректный формат данных API /groups.")
        return None

    faculty_groups_api: dict[str, list[str]] = {}
    for group in data["groups"]:
        faculty_name = group.get("facultyName")
        group_name = group.get("groupName")
        if not faculty_name or not group_name:
            continue
        faculty_groups_api.setdefault(faculty_name, []).append(group_name)

    if not faculty_groups_api:
        logger.warning("Нет доступных групп ни в БД, ни в API.")
        return None

    logger.info("Клавиатуры групп успешно созданы из API.")
    return build_faculty_keyboards(faculty_groups_api)