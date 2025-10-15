# """
# Модуль для создания клавиатур (inline) в Telegram-боте для работы с расписанием.
#
# Содержит функции для:
# 1. Генерации клавиатуры выбора типа синхронизации (весь университет, факультет, группа).
# 2. Создания универсальной клавиатуры отмены действий с заданным типом.
# 3. Создания клавиатур факультетов и групп факультетов
#    с дополнительной кнопкой отмены именно для сценария синхронизации расписания.
#
# Использует базовые функции:
# - create_faculty_keyboard() — возвращает клавиатуру факультетов без кнопок отмены.
# - create_courses_keyboards() — возвращает словарь клавиатур групп по факультетам без кнопок отмены.
#
# Результат:
# - faculty_keyboard_sync — клавиатура факультетов с кнопкой "Отмена синхронизации".
# - faculty_keyboards_sync — словарь клавиатур групп факультетов с кнопкой "Отмена синхронизации".
# """
#
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# import app.keyboards.base_kb as base_kb
#
# faculty_keyboard_sync = None
# groups_keyboards_sync = None
#
# async def refresh_sync_keyboards():
#     """
#     Пересоздаёт клавиатуры для синхронизации расписания.
#     Вызывать после старта бота и после каждой синхронизации.
#     """
#     if base_kb.faculty_keyboard_base is None or base_kb.groups_keyboards_base is None:
#         await base_kb.refresh_base_keyboards()
#
#     global faculty_keyboard_sync, groups_keyboards_sync
#     faculty_keyboard_sync = await create_faculty_keyboard_sync()
#     groups_keyboards_sync = await create_groups_keyboards_sync()
#
# def get_type_sync_kb():
#     """
#     Создаёт клавиатуру выбора типа синхронизации расписания.
#
#     Кнопки:
#         - Синхронизация расписания для всего университета.
#         - Синхронизация расписания для выбранного факультета.
#         - Синхронизация расписания для отдельной группы.
#
#     Возвращает:
#         InlineKeyboardMarkup: объект клавиатуры.
#     """
#
#     kb = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="Синхронизация расписания для всех", callback_data="sync_university")],
#             [InlineKeyboardButton(text="Синхронизация расписания для факультета", callback_data="sync_faculty")],
#             [InlineKeyboardButton(text="Синхронизация расписания для группы", callback_data="sync_group")],
#             [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_choice_sync")]
#         ]
#     )
#
#     return kb
#
# async def create_faculty_keyboard_sync():
#     """
#     Создаёт клавиатуру факультетов для синхронизации расписания.
#
#     Основные кнопки — список факультетов (из create_faculty_keyboard),
#     в конец добавляется кнопка:
#         ❌ Отмена
#
#     Returns:
#         InlineKeyboardMarkup | None:
#             - клавиатура факультетов с кнопкой отмены,
#             - None, если базовая клавиатура отсутствует.
#     """
#
#     kb = base_kb.faculty_keyboard_base
#     if kb is None:
#         return None
#
#     new_kb = InlineKeyboardMarkup(
#         inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
#             [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_faculty_sync")]
#         ]
#     )
#     return new_kb
#
# async def create_groups_keyboards_sync():
#     """
#     Создаёт словарь клавиатур групп факультетов для синхронизации расписания.
#
#     Для каждого факультета берётся базовая клавиатура групп (из create_courses_keyboards),
#     в конец каждой клавиатуры добавляется кнопка:
#         ❌ Отмена
#
#     Returns:
#         dict[str, InlineKeyboardMarkup] | None:
#             - словарь {faculty_name: клавиатура с группами и кнопкой отмены},
#             - None, если базовые клавиатуры отсутствуют.
#     """
#
#     base = base_kb.groups_keyboards_base
#     if base is None:
#         return None
#
#     faculty_kb = {}
#     for faculty, kb in base.items():
#         new_kb = InlineKeyboardMarkup(
#             inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
#                 [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_sync")]
#             ]
#         )
#         faculty_kb[faculty] = new_kb
#
#     return faculty_kb

"""
Клавиатуры для синхронизации расписания с API.

Создаёт:
1. type_sync_kb — выбор типа синхронизации (университет, факультет, группа).
2. faculty_keyboard_sync — клавиатура факультетов с кнопкой отмены.
3. groups_keyboards_sync — словарь клавиатур групп факультетов с кнопкой отмены.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.schedule.fetcher import TimetableClient
import logging

from app.keyboards.base_kb import faculty_abbr

logger = logging.getLogger(__name__)

faculty_keyboard_sync = None
groups_keyboards_sync = None

async def refresh_sync_keyboards():
    """
    Пересоздаёт клавиатуры для синхронизации расписания.
    Берёт данные напрямую с API.
    """
    global faculty_keyboard_sync, groups_keyboards_sync

    client = TimetableClient()
    try:
        data = await client.fetch_groups()
    except Exception as e:
        logger.error(f"Не удалось получить данные групп с API: {e}")
        faculty_keyboard_sync = None
        groups_keyboards_sync = None
        await client.close()
        return

    await client.close()

    if not data or "groups" not in data:
        logger.warning("API вернул некорректные данные: 'groups' отсутствует")
        faculty_keyboard_sync = None
        groups_keyboards_sync = None
        return

    # --- Формируем список факультетов ---
    faculties = sorted({group['facultyName'] for group in data['groups']})
    faculty_keyboard_sync = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f, callback_data=f"faculty:{faculty_abbr.get(f, f)}")]
            for f in faculties
        ] + [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_faculty_sync")]]
    )

    # --- Формируем словарь клавиатур групп по факультетам ---
    faculty_groups: dict[str, list[str]] = {}
    for group in data['groups']:
        faculty = group.get("facultyName")
        group_name = group.get("groupName")
        if not faculty or not group_name:
            continue
        faculty_groups.setdefault(faculty, []).append(group_name)

    groups_keyboards_sync = {}
    for faculty, groups in faculty_groups.items():
        groups.sort()
        keyboard = []
        row = []
        for i, group_name in enumerate(groups):
            row.append(InlineKeyboardButton(text=group_name, callback_data=f"group:{group_name}"))
            if len(row) == 3 or i == len(groups) - 1:
                keyboard.append(row)
                row = []
        # Добавляем кнопку "Отмена" в конец клавиатуры факультета
        keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_sync")])
        groups_keyboards_sync[faculty] = InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_type_sync_kb():
    """
    Создаёт клавиатуру выбора типа синхронизации расписания.

    Кнопки:
        - Синхронизация расписания для всего университета.
        - Синхронизация расписания для выбранного факультета.
        - Синхронизация расписания для отдельной группы.
        - Отмена
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Синхронизация расписания для всех", callback_data="sync_university")],
            [InlineKeyboardButton(text="Синхронизация расписания для факультета", callback_data="sync_faculty")],
            [InlineKeyboardButton(text="Синхронизация расписания для группы", callback_data="sync_group")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_choice_sync")]
        ]
    )
