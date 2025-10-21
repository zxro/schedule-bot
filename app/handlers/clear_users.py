import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from sqlalchemy import delete
from app.database.db import AsyncSessionLocal
from app.database.models import User
from app.config import settings
from app.filters.is_admin import IsAdminFilter
from app.state.states import DeleteUsersBDStates
from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data=="cancel_delete_users", IsAdminFilter())
async def cancel_delete_users(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Удаление БД с пользователями отменено")
    await callback.answer()

    await asyncio.sleep(1)
    await callback.message.delete()


@router.callback_query(F.data=="clear_user_db", IsAdminFilter())
async def clear_user_db(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="⚠️ Эта операция удалит всех пользователей, кроме администраторов.\nВведите пароль для подтверждения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete_users")]
        ]))

    await callback.answer()
    await state.set_state(DeleteUsersBDStates.confirm_delete)
    await state.update_data(confirm_message_id=callback.message.message_id)


@router.message(StateFilter(DeleteUsersBDStates.confirm_delete), IsAdminFilter())
async def confirm_delete_user(message: Message, state: FSMContext):
    """
    Удаляет всех пользователей, кроме администраторов, из базы данных.

    Проверяет пароль подтверждения (ADMIN_PASSWORD из config.py).

    Логика:
    1. Запрашивает пароль у оператора через консоль.
    2. Проверяет введённый пароль.
       - Если неверный — операция отменяется.
    3. Подключается к БД.
    4. Выполняет удаление всех записей из таблицы `users`,
       где `role != 1` (то есть не администраторы).
    5. Фиксирует изменения.
    6. Выводит отчёт о количестве удалённых пользователей.

    Важно:
    - Администраторы (role = 1) не удаляются.
    - Действие необратимо!.
    """

    data = await state.get_data()
    confirm_message_id = data.get('confirm_message_id')

    if confirm_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=confirm_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с подтверждением: {e}")

    password = message.text
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить сообщение пользователя с паролем: {e}")

    if password != settings.ADMIN_PASSWORD:
        logger.warning("❌ Попытка очистки базы с неверным паролем.")

        try:
            msg = await message.answer("❌ Неверный пароль")

            await asyncio.sleep(1.5)

            try:
                await msg.delete()
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить сообщение 'Неверный пароль': {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка при отправке сообщения 'Неверный пароль': {e}")

        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        try:
            stmt = delete(User).where(User.role != 1)
            result = await session.execute(stmt)
            await session.commit()

            deleted_count = result.rowcount or 0

            txt = f"✅ Из базы удалено {deleted_count} пользователей (остались только админы)."
            await message.answer(txt)
            logger.info(txt)
            await send_chat_info_log(txt)

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка при удалении пользователей: {e}")

    await state.clear()