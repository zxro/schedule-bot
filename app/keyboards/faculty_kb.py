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
import requests
from app.config import settings
import logging

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

# ================= ЗАГРУЗКА ДАННЫХ =================

def load_groups_data():
    """
    Загружает данные групп из внешнего API (settings.TIMETABLE_API_BASE + "/groups").

    Возвращает:
        dict: JSON-ответ от сервера (обычно содержит ключ 'groups'), если успешно.
        None: при ошибке (в этом случае ошибка залогирована).
    """

    url = settings.TIMETABLE_API_BASE + "/groups"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при загрузке данных из API: {e}")


# ================= ФАКУЛЬТЕТЫ =================

def create_faculty_keyboard():
    """
    Создаёт клавиатуру факультетов (без кнопки отмены).

    Логика:
        - Загружает список групп через load_groups_data().
        - Извлекает уникальные факультеты.
        - Для каждого факультета создаёт кнопку с callback_data вида "faculty:<ABBR>".

    Возвращает:
        InlineKeyboardMarkup | None:
            - InlineKeyboardMarkup — клавиатура со списком факультетов.
            - None — если данные недоступны или не удалось создать клавиатуру.
    """

    data = load_groups_data()
    if data is None:
        return None

    faculties = sorted(set(group['facultyName'] for group in data['groups']))
    keyboard = []
    for faculty in faculties:
        abbr = faculty_abbr.get(faculty)
        if not abbr:
            logger.warning("Факультет '%s' не найден в faculty_abbr — пропуск.", faculty)
            continue
        keyboard.append([InlineKeyboardButton(text=faculty, callback_data=f"faculty:{abbr}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# # ================= ГРУППЫ =================
def create_courses_keyboards():
    """
    Создаёт словарь клавиатур для групп факультетов (без кнопки отмены).

    Логика:
        - Загружает список групп через load_groups_data().
        - Группирует их по факультетам.
        - Для каждого факультета создаётся клавиатура, где группы расположены по 3 кнопки в ряд.

    Возвращает:
        dict[str, InlineKeyboardMarkup] | None:
            - словарь {facultyName: InlineKeyboardMarkup} — клавиатуры для каждого факультета.
            - None — если данные недоступны или не удалось построить клавиатуры.
    """

    data = load_groups_data()
    if data is None:
        return None

    faculties = {}
    for group in data['groups']:
        faculty = group['facultyName']
        group_name = group['groupName']
        faculties.setdefault(faculty, []).append(group_name)

    for faculty in faculties:
        faculties[faculty].sort()

    faculty_kb = {}
    for faculty, groups in faculties.items():
        keyboard = []
        row = []
        for i, group in enumerate(groups):
            row.append(InlineKeyboardButton(text=group, callback_data=f"group:{group}"))
            if len(row) == 3 or i == len(groups) - 1:
                keyboard.append(row)
                row = []
        faculty_kb[faculty] = InlineKeyboardMarkup(inline_keyboard=keyboard)

    return faculty_kb
