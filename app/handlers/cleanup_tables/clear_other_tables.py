import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from sqlalchemy import delete
from app.database.db import AsyncSessionLocal
from app.database.models import Faculty, Group, Lesson, Professor, ProfessorLesson
from app.config import settings
from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin_kb import get_admin_kb
from app.state.states import DeleteSyncTablesStates
from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log


logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data=="cancel_clear_sync_tables", IsAdminFilter())
async def cancel_clear_sync_tables(callback: CallbackQuery, state: FSMContext):
    """
    Отмена операции удаления данных из таблиц синхронизации БД.

    Логика:
        - Состояние FSM очищается.
        - Сообщение с предупреждением заменяется текстом об отмене.
        - Сообщение возвращается в интерфейс админ панели.
    """

    await state.clear()
    await callback.message.edit_text("❌ Очистка таблиц синхронизации отменена")
    await callback.answer()
    await asyncio.sleep(1)
    await callback.message.edit_text(text="Админ панель:", reply_markup=get_admin_kb())


@router.callback_query(F.data=="clear_sync_tables", IsAdminFilter())
async def clear_sync_tables(callback: CallbackQuery, state: FSMContext):
    """
    Инициирует процесс удаления данных из таблиц: Faculty, Group, Lesson, Professor, ProfessorLesson.

    Функция отправляет предупреждение и переводит FSM в состояние ожидания пароля подтверждения.
    """

    await callback.message.edit_text(
        text="⚠️ Эта операция удалит данные из таблиц: факультетов, групп, пар студентов, преподавателей, пар преподавателей.\n"
             "Введите пароль для подтверждения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_clear_sync_tables")]
        ])
    )

    await callback.answer()
    await state.set_state(DeleteSyncTablesStates.confirm_delete)
    await state.update_data(confirm_message_id=callback.message.message_id)


@router.message(StateFilter(DeleteSyncTablesStates.confirm_delete), IsAdminFilter())
async def confirm_clear_sync_tables(message: Message, state: FSMContext):
    """
    Завершает очистку всех таблиц Faculty, Group, Lesson, Professor, ProfessorLesson после подтверждения паролем.

    Логика работы:
        1. Удаляет сообщение с запросом пароля (если есть).
        2. Проверяет пароль (ADMIN_PASSWORD).
        3. При успешной проверке подключается к БД.
        4. Выполняет поочередное удаление всех записей из таблиц: ProfessorLesson, Lesson, Professor, Group, Faculty.
        5. Фиксирует транзакцию.
        6. Отправляет сообщение об успешной очистке.
        7. Очищает состояние FSM.

    Исключения:
        - Ошибки удаления сообщений Telegram.
        - Ошибки SQLAlchemy при удалении данных.
        - Ошибки подключения к базе данных.
    """
    
    data = await state.get_data()
    confirm_message_id = data.get("confirm_message_id")

    if confirm_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=confirm_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с подтверждением очистки таблиц: {e}")

    password = message.text
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить сообщение пользователя с паролем: {e}")

    if password != settings.ADMIN_PASSWORD:
        logger.warning("❌ Попытка очистки остальных таблиц с неверным паролем.")
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
            for model, name in [(ProfessorLesson, "ProfessorLesson"),
                                (Lesson, "Lesson"),
                                (Professor, "Professor"),
                                (Group, "Group"),
                                (Faculty, "Faculty")]:
                stmt = delete(model)
                result = await session.execute(stmt)
                logger.info(f"Удалено {result.rowcount or 0} записей из таблицы {name}.")

            await session.commit()
            txt = "✅ Таблицы Faculty, Group, Lesson, Professor, ProfessorLesson успешно очищены."
            await message.answer(txt)
            logger.info(txt)
            await send_chat_info_log(txt)

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка при очистке таблиц синхронизации: {e}")

    await state.clear()