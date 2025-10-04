from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_type_sync_kb():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Синхронизация расписания для всех", callback_data="sync_university")],
            [InlineKeyboardButton(text="Синхронизация расписания для факультета", callback_data="sync_faculty")],
            [InlineKeyboardButton(text="Синхронизация расписания для группы", callback_data="sync_group")],
        ]
    )

    return kb