from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_kb():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Синхронизировать расписание", callback_data="sync_schedule")],
            [InlineKeyboardButton(text="Добавить администратора", callback_data="add_admin")],
            [InlineKeyboardButton(text="Список администраторов", callback_data="list_of_admins")],
            [InlineKeyboardButton(text="Очистить БД пользователей", callback_data="clear_user_db")],
            [InlineKeyboardButton(text="Выйти", callback_data="exit_admin_panel")],
        ],
        resize_keyboard=True
    )

    return keyboard