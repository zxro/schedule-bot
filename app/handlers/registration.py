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

from app.utils.messages.safe_delete_messages import safe_delete_callback_message

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("cancel_"), F.data.endswith("_reg"))
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    try:
        await safe_delete_callback_message(callback)
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение: {e}")


@router.message(F.text == "Регистрация")
async def start_registration(message: Message, state: FSMContext):
    """Начало процесса регистрации с проверкой существующей регистрации"""
    # Проверяем, зарегистрирован ли пользователь
    async with AsyncSessionLocal() as session:
        query = await session.execute(select(User).where(User.id == message.from_user.id))
        existing_user = query.scalars().first()

    if existing_user:
        # Пользователь уже зарегистрирован
        await message.answer(
            "✅ Вы уже зарегистрированы!\n\n"
            "Вы можете использовать полный функционал бота.\n"
            "Если хотите изменить данные, используйте раздел \"Прочие функции\" → \"Изменить персональные данные\"",
            reply_markup=await get_main_menu_kb(message.from_user.id)
        )
        return

    # Если пользователь не зарегистрирован, начинаем процесс регистрации
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

    try:
        async with AsyncSessionLocal() as session:
            # Находим группу и факультет в базе
            query = await session.execute(select(Group).where(Group.group_name == group_name))
            group = query.scalars().first()

            query = await session.execute(select(Faculty).where(Faculty.name == faculty_name))
            faculty = query.scalars().first()

            if not group or not faculty:
                await callback.message.edit_text("❌ Ошибка: группа или факультет не найдены.")
                return

            # Проверяем, есть ли уже пользователь
            query = await session.execute(select(User).where(User.id == callback.from_user.id))
            existing_user = query.scalars().first()

            if existing_user:
                # Обновляем существующего пользователя
                existing_user.group_id = group.id
                existing_user.faculty_id = faculty.id
                action_text = "Данные обновлены!"
                success_message = f"✅ Данные обновлены!\nФакультет: {faculty_name}\nГруппа: {group_name}"
            else:
                # Создаем нового пользователя
                user = User(
                    id=callback.from_user.id,
                    group_id=group.id,
                    faculty_id=faculty.id
                )
                session.add(user)
                action_text = "Регистрация завершена!"
                success_message = (
                    f"✅ Регистрация завершена!\n"
                    f"Факультет: {faculty_name}\n"
                    f"Группа: {group_name}\n\n"
                    f"Теперь вы можете быстро просматривать своё расписание"
                )

            await session.commit()

        # Получаем обновленную клавиатуру для зарегистрированного пользователя
        updated_keyboard = await get_main_menu_kb(callback.from_user.id)

        # Отправляем сообщение с обновленной клавиатурой
        await callback.message.answer(success_message, reply_markup=updated_keyboard)

        # Редактируем предыдущее сообщение, чтобы убрать инлайн-клавиатуру
        await callback.message.edit_text(f"✅ {action_text}")
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        await callback.message.edit_text("❌ Ошибка при регистрации. Попробуйте позже.")
    finally:
        await state.clear()