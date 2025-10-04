from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_sync_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Синхронизация расписания для ПМиК-37")],
            [KeyboardButton(text="Показать расписание ПМиК-37")]
        ],
        resize_keyboard=True
    )
    return kb