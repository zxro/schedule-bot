from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_sync_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Синхронизация расписания для всех")],
            [KeyboardButton(text="Синхронизация расписания для факультета")],
            [KeyboardButton(text="Синхронизация расписания для группы")],
        ],
        resize_keyboard=True
    )
    return kb