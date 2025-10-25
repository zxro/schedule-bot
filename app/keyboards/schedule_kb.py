from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_choice_week_type_kb():
    """Возвращает клавиатуру выбора типа недели расписания студента."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Неделя ➖", callback_data=f"week:minus")],
            [InlineKeyboardButton(text="Неделя ➕", callback_data=f"week:plus")],
            [InlineKeyboardButton(text="Полное расписание", callback_data=f"week:full")]
        ]
    )

    return kb


def get_schedule_professors_kb(professor_name: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора типа расписания для преподавателя."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data=f"prof_today:{professor_name}")],
            [
                InlineKeyboardButton(text="➕ Неделя", callback_data=f"prof_week_plus:{professor_name}"),
                InlineKeyboardButton(text="➖ Неделя", callback_data=f"prof_week_minus:{professor_name}")
            ],
            [InlineKeyboardButton(text="🗓 Вся неделя", callback_data=f"prof_week_full:{professor_name}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="cancel")]
        ]
    )

def get_other_schedules_kb():
    """Возвращает клавиатуру выбора типа расписания для студента."""
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
