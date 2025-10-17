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
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Расписание на сегодня")],
                [KeyboardButton(text="Другие расписания")],
                [KeyboardButton(text="Прочие функции")],
                [KeyboardButton(text="Админ панель")]  # В будущем добавлять эту кнопку только при проверке на роль
            ],
            resize_keyboard=True
        )
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Регистрация")],
                [KeyboardButton(text="Расписания")],
                # [KeyboardButton(text="Прочие функции")] # убрано в связи с отсутствием регистрации
            ],
            resize_keyboard=True
        )

    return keyboard