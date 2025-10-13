from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def choice_week_kb():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Неделя ➖", callback_data=f"week:minus")],
            [InlineKeyboardButton(text="Неделя ➕", callback_data=f"week:plus")],
            [InlineKeyboardButton(text="Полное расписание", callback_data=f"week:full")]
        ]
    )

    return kb
