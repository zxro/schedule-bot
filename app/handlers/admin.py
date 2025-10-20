import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin_kb import get_admin_kb

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data=="exit_admin_panel", IsAdminFilter())
async def exit_admin_panel(callback: CallbackQuery):
    await callback.message.delete()


@router.message(F.text == "Админ панель", IsAdminFilter())
async def admin_panel(message: Message):
    await message.answer(text="Админ панель:", reply_markup=get_admin_kb())