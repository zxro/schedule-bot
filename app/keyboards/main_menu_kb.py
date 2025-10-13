from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from app.database.db import AsyncSessionLocal
from app.database.models import User
from sqlalchemy import select

async def get_main_menu_kb(user_id: int):
    """
    Создает клавиатуру главного меню в зависимости от статуса регистрации пользователя
    """
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()

    if user:
        # Пользователь зарегистрирован
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Показать мое расписание")],
                [KeyboardButton(text="Просмотреть расписание")],
                [KeyboardButton(text="Синхронизировать расписание")]
            ],
            resize_keyboard=True
        )
    else:
        # Пользователь не зарегистрирован
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Регистрация")],
                [KeyboardButton(text="Просмотреть расписание")],
                [KeyboardButton(text="Синхронизировать расписание")]
            ],
            resize_keyboard=True
        )

    return keyboard