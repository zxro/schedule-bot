"""
Формирование inline-клавиатур для поиска расписания факультетов и групп.

Модуль строит:
    - faculty_keyboard_find: клавиатуру с факультетами и кнопкой отмены поиска.
    - faculty_keyboards_find: словарь {facultyName: InlineKeyboardMarkup}, где каждая клавиатура
      соответствует группам факультета и содержит кнопку отмены поиска.

Основные функции:
    - create_faculty_keyboard_find() — создаёт клавиатуру факультетов с кнопкой отмены поиска.
    - create_courses_keyboards_find() — создаёт словарь клавиатур групп с кнопкой отмены поиска.

Функции используют базовые генераторы клавиатур:
    - create_faculty_keyboard() — для факультетов.
    - create_courses_keyboards() — для групп.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.keyboards.faculty_kb import create_courses_keyboards, create_faculty_keyboard

def create_faculty_keyboard_find():
    """
    Создаёт клавиатуру факультетов для поиска расписания.

    Логика:
        - Использует базовую функцию create_faculty_keyboard().
        - Если данные недоступны (None), возвращает None.
        - К готовой клавиатуре добавляет кнопку "❌ Отмена поиска".

    Возвращает:
        InlineKeyboardMarkup | None:
            - InlineKeyboardMarkup — клавиатура факультетов с кнопкой отмены поиска.
            - None — если базовая клавиатура не создана.
    """

    kb = create_faculty_keyboard()
    if kb is None:
        return None

    new_kb = InlineKeyboardMarkup(
        inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
            [InlineKeyboardButton(text="❌ Отмена поиска", callback_data="cancel_faculty_find")]
        ]
    )
    return new_kb

def create_group_keyboards_find():
    """
    Создаёт словарь клавиатур групп для поиска расписания.

    Логика:
        - Использует базовую функцию create_courses_keyboards().
        - Если данные недоступны (None), возвращает None.
        - Для каждой клавиатуры добавляет кнопку "❌ Отмена поиска".

    Возвращает:
        dict[str, InlineKeyboardMarkup] | None:
            - словарь {facultyName: InlineKeyboardMarkup}, где каждая клавиатура
              содержит группы и кнопку отмены поиска.
            - None — если базовые клавиатуры не созданы.
    """

    base = create_courses_keyboards()
    if base is None:
        return None

    faculty_kb = {}
    for faculty, kb in base.items():
        new_kb = InlineKeyboardMarkup(
            inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
                [InlineKeyboardButton(text="❌ Отмена поиска", callback_data="cancel_group_find")]
            ]
        )
        faculty_kb[faculty] = new_kb

    return faculty_kb

faculty_keyboard_find = create_faculty_keyboard_find()
groups_keyboards_find = create_group_keyboards_find()