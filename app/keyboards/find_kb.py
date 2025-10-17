"""
Модуль для создания inline-клавиатур для поиска расписания факультетов и групп.

Содержит функции для:
1. Генерации клавиатуры факультетов с кнопкой отмены поиска.
2. Генерации словаря клавиатур групп факультетов с кнопкой отмены поиска.
3. Пересоздания клавиатур после обновления данных (например, после синхронизации).

Использует базовые функции:
- create_faculty_keyboard() — возвращает клавиатуру факультетов без кнопок отмены.
- create_courses_keyboards() — возвращает словарь клавиатур групп по факультетам без кнопок отмены.

Результат:
- faculty_keyboard_find — клавиатура факультетов с кнопкой "Отмена поиска".
- groups_keyboards_find — словарь клавиатур групп факультетов с кнопкой "Отмена поиска".
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import app.keyboards.base_kb as base_kb

faculty_keyboard_find = None
groups_keyboards_find = None

async def refresh_find_keyboards():
    """
    Пересоздаёт клавиатуры для поиска расписания.
    Вызывать после старта бота и после каждой синхронизации данных.
    """
    if base_kb.faculty_keyboard_base is None or base_kb.groups_keyboards_base is None:
        await base_kb.refresh_base_keyboards()

    global faculty_keyboard_find, groups_keyboards_find
    faculty_keyboard_find = await create_faculty_keyboard_find()
    groups_keyboards_find = await create_groups_keyboards_find()

async def create_faculty_keyboard_find():
    """
    Создаёт клавиатуру факультетов для поиска расписания.

    Основные кнопки — список факультетов (из create_faculty_keyboard),
    в конец добавляется кнопка:
        ❌ Отмена

    Returns:
        InlineKeyboardMarkup | None:
            - клавиатура факультетов с кнопкой отмены,
            - None, если базовая клавиатура отсутствует.
    """

    kb = base_kb.faculty_keyboard_base
    if kb is None:
        return None

    new_kb = InlineKeyboardMarkup(
        inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_faculty_find")]
        ]
    )
    return new_kb


async def create_groups_keyboards_find():
    """
    Создаёт словарь клавиатур групп факультетов для поиска расписания.

    Для каждого факультета берётся базовая клавиатура групп (из create_courses_keyboards),
    в конец каждой клавиатуры добавляется кнопка:
        ❌ Отмена

    Returns:
        dict[str, InlineKeyboardMarkup] | None:
            - словарь {faculty_name: клавиатура с группами и кнопкой отмены},
            - None, если базовые клавиатуры отсутствуют.
    """

    base = base_kb.groups_keyboards_base
    if base is None:
        return None

    faculty_kb = {}
    for faculty, kb in base.items():
        new_kb = InlineKeyboardMarkup(
            inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_find")]
            ]
        )
        faculty_kb[faculty] = new_kb

    return faculty_kb