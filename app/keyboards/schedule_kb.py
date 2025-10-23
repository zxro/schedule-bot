from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_choice_week_kb():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Неделя ➖", callback_data=f"week:minus")],
            [InlineKeyboardButton(text="Неделя ➕", callback_data=f"week:plus")],
            [InlineKeyboardButton(text="Полное расписание", callback_data=f"week:full")]
        ]
    )

    return kb

def get_other_schedules_kb():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="На текущую неделю", callback_data="weekly_schedule"),
                InlineKeyboardButton(text="На следующую неделю", callback_data="next_week_schedule")
            ],
            [
                InlineKeyboardButton(text="Расписание преподавателя", callback_data="professor_schedule")
            ],
            [
                InlineKeyboardButton(text="Другое расписание", callback_data="other_schedule")
            ],
            [
                InlineKeyboardButton(text="Выйти", callback_data="exit_other_schedules")
            ]
        ]
    )

    return kb
