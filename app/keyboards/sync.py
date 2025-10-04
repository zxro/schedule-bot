from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_sync_keyboard():
    kb = InlineKeyboardMarkup(
        keyboard=[
            [InlineKeyboardButton(text="Синхронизация расписания для ПМиК-37")],
            [InlineKeyboardButton(text="Показать расписание ПМиК-37")]
        ],
        resize_keyboard=True
    )
    return kb