from aiogram.types import CallbackQuery
from aiogram import F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.utils.messages.safe_delete_messages import safe_delete_callback_message
from app.keyboards.schedule_kb import get_other_schedules_kb

router = Router()


@router.callback_query(F.data == "bells_schedule")
async def show_bells_schedule(callback: CallbackQuery):
    """Показывает полное расписание звонков"""
    bells_schedule = (
        "🔔 *Расписание звонков:*\n\n"
        "• 1 пара: 8:30 - 10:05\n"
        "• 2 пара: 10:15 - 11:50\n"
        "• 3 пара: 12:10 - 13:45\n"
        "• 4 пара: 14:00 - 15:35\n"
        "• 5 пара: 15:55 - 17:30\n"
        "• 6 пара: 17:45 - 19:20\n"
        "• 7 пара: 19:30 - 21:00"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_other_schedules")]
        ]
    )

    await callback.message.edit_text(bells_schedule, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "back_to_other_schedules")
async def back_to_other_schedules(callback: CallbackQuery):
    """Возврат к меню других расписаний"""
    await callback.message.edit_text(
        "Выберите расписание которое хотите посмотреть:",
        reply_markup=get_other_schedules_kb()
    )
    await callback.answer()