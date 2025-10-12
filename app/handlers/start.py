from aiogram import Router, types
from aiogram.filters import CommandStart
from app.keyboards.main_menu_kb import get_main_menu_kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start с динамическим меню"""
    keyboard = await get_main_menu_kb(message.from_user.id)
    await message.answer(
        text="Привет! Я твой бот, буду помогать с расписанием 🤖",
        reply_markup=keyboard
    )