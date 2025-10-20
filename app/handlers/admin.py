import logging
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import update, select

from app.database.models import User
from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin_kb import get_admin_kb
from app.state.states import AddAdminStates
from app.database.db import AsyncSessionLocal

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data=="exit_admin_panel", IsAdminFilter())
async def exit_admin_panel(callback: CallbackQuery):
    await callback.message.delete()


@router.message(F.text == "Админ панель", IsAdminFilter())
async def admin_panel(message: Message):
    await message.answer(text="Админ панель:", reply_markup=get_admin_kb())


@router.callback_query(F.data == "add_admin", IsAdminFilter())
async def add_admin(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ID пользователя для назначения администратором:")
    await state.set_state(AddAdminStates.waiting_id)
    await callback.answer()


@router.message(StateFilter(AddAdminStates.waiting_id), IsAdminFilter())
async def reading_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                await message.answer(f"❌ Пользователь с ID {user_id} не найден.")
                logger.info(f"⚠️ Попытка назначить администратором несуществующего пользователя {user_id}")
                await state.clear()
                return

            if user.role == 1:
                await message.answer(f"ℹ️ Пользователь {user_id} уже является администратором")
                logger.info(f"ℹ️ Попытка назначить администратором пользователя {user_id}, который уже им является")
                await state.clear()
                return

            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(role=1)
            )
            await session.commit()

            success_message = f"✅ Пользователь {user_id} назначен администратором"
            await message.answer(success_message)
            logger.info(success_message)

    except ValueError as e:
        await message.answer("❌ Неверный формат ID. Введите числовой ID.")
        logger.error(f"❌ Ошибка при преобразовании ID '{message.text}' в handler reading_id: {e}")

    except Exception as e:
        await message.answer("❌ Произошла ошибка при обработке ID.")
        logger.error(f"❌ Неожиданная ошибка в reading_id для текста '{message.text}': {e}")

    finally:
        await state.clear()


@router.callback_query(F.data == "list_of_admins", IsAdminFilter())
async def list_admins(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.role == 1)
        result = await session.execute(stmt)
        admins = result.scalars().all()

        if not admins:
            await callback.message.edit_text(
                text="📋 Список администраторов пуст",
                reply_markup=InlineKeyboardBuilder()
                .button(text="◀️ Выйти", callback_data="exit_admin_panel")
                .as_markup()
            )
            await callback.answer()
            return

        admin_list = "📋 Список администраторов:\n\n"
        for i, admin in enumerate(admins, 1):
            admin_list += f"{i}. ID: {admin.id}\n"
            if admin.id == callback.from_user.id:
                admin_list += f"   ⭐ Это вы\n"

        builder = InlineKeyboardBuilder()

        for admin in admins:
            if admin.id != callback.from_user.id:
                builder.button(
                    text=f"🗑️ Удалить {admin.id}",
                    callback_data=f"remove_admin_{admin.id}"
                )

        builder.button(text="◀️ Выйти", callback_data="exit_admin_panel")

        builder.adjust(1)

        await callback.message.edit_text(
            admin_list,
            reply_markup=builder.as_markup()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("remove_admin_"), IsAdminFilter())
async def remove_admin_handler(callback: CallbackQuery):
    try:
        admin_id = int(callback.data.split("_")[2])

        if admin_id == callback.from_user.id:
            await callback.answer("❌ Вы не можете снять права с самого себя", show_alert=True)
            return

        async with AsyncSessionLocal() as session:
            user = await session.get(User, admin_id)
            if not user:
                await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

            await session.execute(
                update(User)
                .where(User.id == admin_id)
                .values(role=0)
            )
            await session.commit()

        txt = f"ID: {admin_id} снят с должности администратора."
        logger.info(txt)
        await callback.message.edit_text(txt)
        await callback.answer()

    except (ValueError, IndexError) as e:
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
        logger.error(f"❌ Ошибка в при снятии роли администратора: {e}")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        logger.error(f"❌ Ошибка в при снятии роли администратора: {e}")