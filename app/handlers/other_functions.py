from aiogram.types import Message, CallbackQuery
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import app.keyboards.registration_kb as registration_kb
from app.state.states import RegistrationStates
from app.utils.messages.safe_delete_messages import safe_delete_message

router = Router()


@router.message(F.text == "Прочие функции")
async def other_functions(message: Message):
    """Меню прочих функций"""
    await safe_delete_message(message)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить персональные данные", callback_data="change_personal_data")],
            [InlineKeyboardButton(text="Назад", callback_data="exit_other_functions")]
        ]
    )
    await message.answer("Выберите действие:", reply_markup=kb)


@router.callback_query(F.data == "change_personal_data")
async def change_personal_data(callback: CallbackQuery, state: FSMContext):
    """Запуск процесса изменения персональных данных"""
    await callback.message.edit_text("Выберите ваш факультет:", reply_markup=registration_kb.faculty_keyboard_reg)
    await state.set_state(RegistrationStates.choice_faculty)
    await callback.answer()


@router.callback_query(F.data == "exit_other_functions")
async def exit_other_functions(callback: CallbackQuery):
    """Выход из меню прочих функций"""
    await callback.message.delete()
    await callback.answer()