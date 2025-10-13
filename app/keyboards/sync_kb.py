"""
Модуль для создания клавиатур (inline) в Telegram-боте для работы с расписанием.

Содержит функции для:
1. Генерации клавиатуры выбора типа синхронизации (весь университет, факультет, группа).
2. Создания универсальной клавиатуры отмены действий с заданным типом.
3. Создания клавиатур факультетов и групп факультетов
   с дополнительной кнопкой отмены именно для сценария синхронизации расписания.

Использует базовые функции:
- create_faculty_keyboard() — возвращает клавиатуру факультетов без кнопок отмены.
- create_courses_keyboards() — возвращает словарь клавиатур групп по факультетам без кнопок отмены.

Результат:
- faculty_keyboard_sync — клавиатура факультетов с кнопкой "Отмена синхронизации".
- faculty_keyboards_sync — словарь клавиатур групп факультетов с кнопкой "Отмена синхронизации".
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.faculty_kb import create_faculty_keyboard, create_courses_keyboards


def get_type_sync_kb():
    """
    Создаёт клавиатуру выбора типа синхронизации расписания.

    Кнопки:
        - Синхронизация расписания для всего университета.
        - Синхронизация расписания для выбранного факультета.
        - Синхронизация расписания для отдельной группы.

    Возвращает:
        InlineKeyboardMarkup: объект клавиатуры.
    """

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Синхронизация расписания для всех", callback_data="sync_university")],
            [InlineKeyboardButton(text="Синхронизация расписания для факультета", callback_data="sync_faculty")],
            [InlineKeyboardButton(text="Синхронизация расписания для группы", callback_data="sync_group")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_choice_sync")]
        ]
    )

    return kb

def create_faculty_keyboard_sync():
    """
    Создаёт клавиатуру факультетов для синхронизации расписания.

    Основные кнопки — список факультетов (из create_faculty_keyboard),
    в конец добавляется кнопка:
        ❌ Отмена

    Returns:
        InlineKeyboardMarkup | None:
            - клавиатура факультетов с кнопкой отмены,
            - None, если базовая клавиатура отсутствует.
    """

    kb = create_faculty_keyboard()
    if kb is None:
        return None

    new_kb = InlineKeyboardMarkup(
        inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_faculty_sync")]
        ]
    )
    return new_kb

def create_groups_keyboards_sync():
    """
    Создаёт словарь клавиатур групп факультетов для синхронизации расписания.

    Для каждого факультета берётся базовая клавиатура групп (из create_courses_keyboards),
    в конец каждой клавиатуры добавляется кнопка:
        ❌ Отмена

    Returns:
        dict[str, InlineKeyboardMarkup] | None:
            - словарь {faculty_name: клавиатура с группами и кнопкой отмены},
            - None, если базовые клавиатуры отсутствуют.
    """

    base = create_courses_keyboards()
    if base is None:
        return None

    faculty_kb = {}
    for faculty, kb in base.items():
        new_kb = InlineKeyboardMarkup(
            inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_sync")]
            ]
        )
        faculty_kb[faculty] = new_kb

    return faculty_kb

faculty_keyboard_sync = create_faculty_keyboard_sync()
groups_keyboards_sync = create_groups_keyboards_sync()