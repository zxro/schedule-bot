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
from app.keyboards.admin_kb import get_admin_kb
from app.state.states import DeleteUsersBDStates
from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data=="cancel_delete_users", IsAdminFilter())
async def cancel_delete_users(callback: CallbackQuery, state: FSMContext):
    """
    Отмена операции удаления всех пользователей из базы данных.

    Когда администратор нажимает кнопку «Отмена», состояние FSM очищается,
    сообщение с предупреждением заменяется текстом об отмене операции,
    после чего сообщение автоматически удаляется через 1 секунду.

    Параметры:
        callback (CallbackQuery): Объект callback, содержащий данные нажатой кнопки.
        state (FSMContext): Контекст конечного автомата состояний (FSM).

    Логика работы:
        - Отправляет пользователю сообщение об отмене операции.
        - Удаляет сообщение после короткой задержки.

    Исключения:
        Exception: Логирует ошибки удаления сообщения, если Telegram API возвращает ошибку.
    """

    await state.clear()
    await callback.message.edit_text("❌ Удаление БД с пользователями отменено")
    await callback.answer()

    await asyncio.sleep(1)
    await callback.message.edit_text(text="Админ панель:", reply_markup=get_admin_kb())


@router.callback_query(F.data=="clear_user_db", IsAdminFilter())
async def clear_user_db(callback: CallbackQuery, state: FSMContext):
    """
    Инициирует процесс удаления всех пользователей (кроме администраторов).

    Функция вызывается при нажатии на кнопку «Очистить базу пользователей».
    Отправляет администратору предупреждение с запросом пароля подтверждения
    и переводит FSM в состояние ожидания ввода пароля (`DeleteUsersBDStates.confirm_delete`).

    Параметры:
        callback (CallbackQuery): Объект колбэка (нажатие inline-кнопки).
        state (FSMContext): Контекст FSM для сохранения текущего состояния.

    """


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
    Завершает процедуру удаления пользователей из базы данных после подтверждения паролем.

    Проверяет введённый пароль, и если он совпадает с ADMIN_PASSWORD из config.py —
    выполняет полное удаление всех записей пользователей, кроме администраторов (`role != 1`).

    При неверном пароле операция прерывается, а пользователю выводится предупреждение,
    которое автоматически удаляется через несколько секунд.

    Параметры:
        message (Message): Сообщение, содержащее введённый пароль.
        state (FSMContext): Контекст FSM для хранения промежуточных данных (ID сообщений и состояния).

    Логика работы:
        1. Удаляет предыдущее сообщение с запросом пароля (если оно есть).
        2. Проверяет правильность введённого пароля.
           - Если пароль неверен — уведомляет и очищает состояние FSM.
        3. При успешной проверке подключается к базе данных.
        4. Удаляет всех пользователей, где `role != 1`.
        5. Записывает изменения.
        6. Отправляет уведомление о количестве удалённых пользователей.
        7. Очищает состояние FSM.

    Исключения:
        - При ошибке удаления сообщений Telegram.
        - При ошибке выполнения SQL-запроса.
        - При ошибке подключения к БД.
    """

    data = await state.get_data()
    confirm_message_id = data.get('confirm_message_id')

    if confirm_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=confirm_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с подтверждением очистки БД: {e}")

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