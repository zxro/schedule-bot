from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from app.database.db import AsyncSessionLocal
from app.database.models import User
from sqlalchemy import select

async def get_main_menu_kb(user_id: int):
    """
    Создает клавиатуру главного меню в зависимости от статуса регистрации и роли пользователя
    """

    async with AsyncSessionLocal() as session:
        q = await session.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()

    if user:
        buttons = [
            [KeyboardButton(text="Расписание на сегодня")],
            [KeyboardButton(text="Другое расписание")],
            [KeyboardButton(text="Прочие функции")]
        ]

        # если роль == 1 -> админ
        if user.role == 1:
            buttons.append([KeyboardButton(text="Админ панель")])

        keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Регистрация")],
                [KeyboardButton(text="Расписания")],
            ],
            resize_keyboard=True
        )

    return keyboard