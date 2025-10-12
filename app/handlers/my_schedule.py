import logging
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup

from app.database.db import AsyncSessionLocal
from app.database.models import User
from app.extracting_schedule.worker import get_schedule_for_group
from app.keyboards.schedule_keyboards import choice_week_kb
from app.state.states import ShowSheduleStates
from sqlalchemy import select

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "Показать мое расписание")
async def show_my_schedule_start(message: Message, state: FSMContext):
    """Начало показа расписания для зарегистрированного пользователя"""
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == message.from_user.id))
        user = q.scalars().first()

    if not user:
        await message.answer(
            "❌ Вы не зарегистрированы. Пожалуйста, пройдите регистрацию сначала.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Регистрация")]],
                resize_keyboard=True
            )
        )
        return

    # Сохраняем группу пользователя в состоянии
    await state.update_data(group_name=user.group.group_name)
    await state.set_state(ShowSheduleStates.choice_week)

    await message.answer("Выберите тип расписания:", reply_markup=choice_week_kb())