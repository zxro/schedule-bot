from aiogram.types import Message
from aiogram import F, Router

router = Router()

@router.message(F.text=="Прочие функции")
async def professor_schedule(message: Message):
    await message.answer("Этот функционал ещё не доступен 😢")
    # реализовать смену факультета и группы