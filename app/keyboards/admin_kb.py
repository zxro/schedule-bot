from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_kb():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Синхронизировать расписание", callback_data="sync_schedule")],
            [InlineKeyboardButton(text="Выйти", callback_data="exit_admin_panel")],
            # остальной функционал
        ],
        resize_keyboard=True
    )

    return keyboard