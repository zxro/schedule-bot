from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from app.config import settings
import logging

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
    """Загружает данные групп из API"""
    url = settings.TIMETABLE_API_BASE + "/groups"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при загрузке данных из API: {e}")


def create_faculty_keyboard():
    """Создает клавиатуру с факультетами"""
    data = load_groups_data()
    if data is None:
        return None

    faculties = sorted(set(group['facultyName'] for group in data['groups']))

    keyboard = [
        [InlineKeyboardButton(text=faculty, callback_data=f"faculty:{faculty_abbr[faculty]}")]
        for faculty in faculties
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_courses_keyboard():
    """Создает клавиатуры с группами для каждого факультета"""
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
    """Возвращает клавиатуру с группами для указанного факультета"""
    return faculty_keyboards.get(faculty_name) if faculty_keyboards else None

def are_keyboards_loaded():
    """Проверяет, успешно ли загружены клавиатуры"""
    return faculty_keyboard is not None and faculty_keyboards is not None