"""
Формирование inline-клавиатур для выбора факультетов и групп на основе данных API.
Модуль загружает список групп (и их факультетов) из внешнего сервиса (settings.TIMETABLE_API_BASE + "/groups")
и формирует:
    - faculty_keyboard: клавиатуру с кнопками для выбора факультета (callback_data -> "faculty:<ABBR>")
    - faculty_keyboards: словарь {facultyName: InlineKeyboardMarkup} с клавиатурами групп внутри факультета

- В файле хранится соответствие полного названия факультета ↔ его аббревиатура (faculty_abbr / abbr_faculty).
- При отсутствии данных от API функции возвращают None и логируют ошибку.
- Кнопки "Отмена" добавлены и имеют callback_data в формате "cancel_*" для единой обработки.
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


def create_faculty_keyboard():
    """
    Создаёт InlineKeyboardMarkup для выбора факультета.

    Логика:
        - Загружает данные через load_groups_data().
        - Берёт уникальные названия факультетов из data['groups'].
        - Для каждого факультета создаёт кнопку с callback_data вида "faculty:<ABBR>".
        - Добавляет строку с кнопкой отмены ("❌ Отмена", callback_data="cancel_faculty_sync").
        - Если API вернёт факультет, которого нет в `faculty_abbr`, то такая запись пропускается и логируется.
          Это предотвращает KeyError при формировании callback_data.

    Возвращает:
        InlineKeyboardMarkup | None:
            - InlineKeyboardMarkup — если данные успешно загружены и найдены сопоставления аббревиатур;
            - None — если не удалось получить данные.
    """
    data = load_groups_data()
    if data is None:
        return None

    faculties = sorted(set(group['facultyName'] for group in data['groups']))

    keyboard = []
    for faculty in faculties:
        abbr = faculty_abbr.get(faculty)
        if not abbr:
            logger.warning("Факультет '%s' не найден в faculty_abbr — пропуск этого факультета.", faculty)
            continue
        keyboard.append([InlineKeyboardButton(text=faculty, callback_data=f"faculty:{abbr}")])

    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_faculty_sync")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_courses_keyboard():
    """
    Создаёт словарь клавиатур для групп по факультетам.

    Логика:
        - Загружает данные через load_groups_data().
        - Группирует группы по полному названию факультета.
        - Для каждого факультета формируется InlineKeyboardMarkup, в котором кнопки с группами
          расположены в строках по 3 элемента.
        - В конце каждой клавиатуры добавляется кнопка "❌ Отмена" с callback_data="cancel_group_sync".

    Возвращает:
        dict[str, InlineKeyboardMarkup] | None:
            - словарь: ключ — полное название факультета, значение — клавиатура групп;
            - None — если не удалось получить данные.
    """

    data = load_groups_data()
    if data is None:
        return None

    faculties = {}
    for group in data['groups']:
        faculty = group['facultyName']
        group_name = group['groupName']

        if faculty not in faculties:
            faculties[faculty] = []
        faculties[faculty].append(group_name)

    for faculty in faculties:
        faculties[faculty].sort()

    faculty_keyboards = {}

    for faculty, groups in faculties.items():
        keyboard = []
        row = []

        for i, group in enumerate(groups):
            row.append(InlineKeyboardButton(text=group, callback_data=f"group:{group}"))

            if len(row) == 3 or i == len(groups) - 1:
                keyboard.append(row)
                row = []

        keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_sync")])
        faculty_keyboards[faculty] = InlineKeyboardMarkup(inline_keyboard=keyboard)

    return faculty_keyboards


faculty_keyboard = create_faculty_keyboard()
faculty_keyboards = create_courses_keyboard()

if faculty_keyboards:
    math_faculty_keyboard = faculty_keyboards.get('Математический факультет')
    pmi_faculty_keyboard = faculty_keyboards.get('Факультет прикладной математики и кибернетики')
    ftech_faculty_keyboard = faculty_keyboards.get('Физико-технический факультет')
    chemistry_faculty_keyboard = faculty_keyboards.get('Химико-технологический факультет')
    aspirantura_keyboard = faculty_keyboards.get('Аспирантура')
    geo_faculty_keyboard = faculty_keyboards.get('Факультет географии и геоэкологии')
    bio_faculty_keyboard = faculty_keyboards.get('Биологический факультет')
    psy_faculty_keyboard = faculty_keyboards.get('Факультет психологии')
    economy_keyboard = faculty_keyboards.get('Институт экономики и управления')
    ped_keyboard = faculty_keyboards.get('Институт педагогического образования и социальных технологий')
    law_keyboard = faculty_keyboards.get('Юридический факультет')
    philology_keyboard = faculty_keyboards.get('Филологический факультет')
    languages_keyboard = faculty_keyboards.get('Факультет иностранных языков и международной коммуникации')
    history_keyboard = faculty_keyboards.get('Исторический факультет')
    sport_keyboard = faculty_keyboards.get('Факультет физической культуры')
else:
    math_faculty_keyboard = None
    pmi_faculty_keyboard = None
    ftech_faculty_keyboard = None
    chemistry_faculty_keyboard = None
    aspirantura_keyboard = None
    geo_faculty_keyboard = None
    bio_faculty_keyboard = None
    psy_faculty_keyboard = None
    economy_keyboard = None
    ped_keyboard = None
    law_keyboard = None
    philology_keyboard = None
    languages_keyboard = None
    history_keyboard = None
    sport_keyboard = None

def get_faculty_groups_keyboard(faculty_name):
    """
    Возвращает клавиатуру с группами для указанного факультета.

    Аргументы:
        faculty_name (str) — полное название факультета, как оно приходит из API / как используется в faculty_keyboards.

    Возвращает:
        InlineKeyboardMarkup | None — соответствующая клавиатура или None, если данные не загружены
        или факультет не найден.
    """

    return faculty_keyboards.get(faculty_name) if faculty_keyboards else None

def are_keyboards_loaded():
    """
    Проверяет, успешно ли загружены клавиатуры при импорте модуля.

    Возвращает:
        bool — True, если и faculty_keyboard, и faculty_keyboards не None.
    """
    return faculty_keyboard is not None and faculty_keyboards is not None