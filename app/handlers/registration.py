import logging
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.database.db import AsyncSessionLocal
from app.database.models import User, Group, Faculty
from app.keyboards.base_kb import abbr_faculty
import app.keyboards.registration_kb as registration_kb
from app.keyboards.main_menu_kb import get_main_menu_kb
from app.state.states import RegistrationStates
from sqlalchemy import select

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("cancel_"), F.data.endswith("_reg"))
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    await callback.message.edit_text("❌ Регистрация отменена.")


@router.message(F.text == "Регистрация")
async def start_registration(message: Message, state: FSMContext):
    """Начало процесса регистрации"""
    await message.answer("Выберите ваш факультет:", reply_markup=registration_kb.faculty_keyboard_reg)
    await state.set_state(RegistrationStates.choice_faculty)


@router.callback_query(StateFilter(RegistrationStates.choice_faculty), F.data.startswith("faculty:"))
async def registration_faculty(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора факультета при регистрации"""
    faculty_abbr = callback.data.split(":")[1]
    faculty_name = abbr_faculty[faculty_abbr]

    groups_kb = registration_kb.groups_keyboards_reg.get(faculty_name)
    if not groups_kb:
        await callback.message.edit_text("❌ Для этого факультета нет групп.")
        return

    await state.update_data(faculty_name=faculty_name, faculty_abbr=faculty_abbr)
    await callback.message.edit_text(
        f"Выберите вашу группу факультета {faculty_name}:",
        reply_markup=groups_kb
    )
    await state.set_state(RegistrationStates.choice_group)


@router.callback_query(StateFilter(RegistrationStates.choice_group), F.data.startswith("group:"))
async def registration_group(callback: CallbackQuery, state: FSMContext):
    """Завершение регистрации - сохранение пользователя"""
    group_name = callback.data.split(":")[1]
    state_data = await state.get_data()
    faculty_name = state_data.get("faculty_name")
    faculty_abbr = state_data.get("faculty_abbr")

    try:
        async with AsyncSessionLocal() as session:
            # Находим группу и факультет в базе
            q = await session.execute(select(Group).where(Group.group_name == group_name))
            group = q.scalars().first()

            q = await session.execute(select(Faculty).where(Faculty.name == faculty_name))
            faculty = q.scalars().first()

            if not group or not faculty:
                await callback.message.edit_text("❌ Ошибка: группа или факультет не найдены.")
                return

            # Проверяем, есть ли уже пользователь
            q = await session.execute(select(User).where(User.id == callback.from_user.id))
            existing_user = q.scalars().first()

            if existing_user:
                # Обновляем существующего пользователя
                existing_user.group_id = group.id
                existing_user.faculty_id = faculty.id
            else:
                # Создаем нового пользователя
                user = User(
                    id=callback.from_user.id,
                    group_id=group.id,
                    faculty_id=faculty.id
                )
                session.add(user)

            await session.commit()

        # Получаем обновленную клавиатуру для зарегистрированного пользователя
        updated_keyboard = await get_main_menu_kb(callback.from_user.id)

        # Отправляем сообщение с обновленной клавиатурой
        await callback.message.answer(
            f"✅ Регистрация завершена!\n"
            f"Факультет: {faculty_name}\n"
            f"Группа: {group_name}\n\n"
            f"Теперь вы можете быстро просматривать своё расписание",
            reply_markup=updated_keyboard
        )

        # Редактируем предыдущее сообщение, чтобы убрать инлайн-клавиатуру
        await callback.message.edit_text("✅ Регистрация завершена!")
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        await callback.message.edit_text("❌ Ошибка при регистрации. Попробуйте позже.")
    finally:
        await state.clear()