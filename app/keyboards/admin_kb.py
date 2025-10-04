from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

def get_admin_kb():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Просмотреть расписание")],
            [KeyboardButton(text="Синхронизировать расписание")]
        ],
        resize_keyboard=True
    )

    return keyboard