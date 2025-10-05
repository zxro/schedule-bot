from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_type_sync_kb():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Синхронизация расписания для всех", callback_data="sync_university")],
            [InlineKeyboardButton(text="Синхронизация расписания для факультета", callback_data="sync_faculty")],
            [InlineKeyboardButton(text="Синхронизация расписания для группы", callback_data="sync_group")],
        ]
    )

    return kb

def get_cancel_kb(cancel_type: str):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{cancel_type}")]
        ]
    )

    return kb