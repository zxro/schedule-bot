from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import app.keyboards.base_kb as base_kb

faculty_keyboard_reg = None
groups_keyboards_reg = None
async def refresh_reg_keyboards():
    """
    Пересоздаёт клавиатуры для регистрации.
    Вызывать после старта бота и после любых изменений групп/факультетов.
    """
    if base_kb.faculty_keyboard_base is None or base_kb.groups_keyboards_base is None:
        await base_kb.refresh_base_keyboards()

    global faculty_keyboard_reg, groups_keyboards_reg
    faculty_keyboard_reg = await create_faculty_keyboard_reg()
    groups_keyboards_reg = await create_group_keyboards_reg()

async def create_faculty_keyboard_reg():
    """
    Создаёт клавиатуру факультетов для регистрации с кнопкой отмены.

    Returns:
        InlineKeyboardMarkup | None:
            - клавиатура факультетов с кнопкой отмены,
            - None, если базовая клавиатура отсутствует.
    """
    base = base_kb.faculty_keyboard_base
    if base is None:
        return None

    new_kb = InlineKeyboardMarkup(
        inline_keyboard=[row.copy() for row in base.inline_keyboard] + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_faculty_reg")]
        ]
    )
    return new_kb

async def create_group_keyboards_reg():
    """
    Создаёт словарь клавиатур групп для регистрации с кнопкой отмены.

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
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_reg")]
            ]
        )
        faculty_kb[faculty] = new_kb

    return faculty_kb