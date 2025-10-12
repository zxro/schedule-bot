from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.keyboards.faculty_kb import create_courses_keyboards, create_faculty_keyboard

def create_faculty_keyboard_reg():
    kb = create_faculty_keyboard()
    if kb is None:
        return None

    new_kb = InlineKeyboardMarkup(
        inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
            [InlineKeyboardButton(text="❌ Отмена регистрации", callback_data="cancel_faculty_reg")]
        ]
    )
    return new_kb

def create_group_keyboards_reg():
    base = create_courses_keyboards()
    if base is None:
        return None

    faculty_kb = {}
    for faculty, kb in base.items():
        new_kb = InlineKeyboardMarkup(
            inline_keyboard=[row.copy() for row in kb.inline_keyboard] + [
                [InlineKeyboardButton(text="❌ Отмена регистрации", callback_data="cancel_group_reg")]
            ]
        )
        faculty_kb[faculty] = new_kb

    return faculty_kb

faculty_keyboard_reg = create_faculty_keyboard_reg()
groups_keyboards_reg = create_group_keyboards_reg()