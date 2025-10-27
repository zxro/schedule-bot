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
