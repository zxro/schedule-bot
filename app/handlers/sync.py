from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import logging

from app.custom_logging.TelegramLogHandler import send_chat_info_log
from app.extracting_schedule.worker import run_full_sync_for_group, run_full_sync, run_full_sync_for_faculty
from app.keyboards.faculty_kb import faculty_keyboard, faculty_keyboards, abbr_faculty
from app.keyboards.sync_kb import get_type_sync_kb, get_cancel_kb

from app.state.states import SyncStates

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("cancel_"))
async def cancel_sync(callback: CallbackQuery, state: FSMContext):
    cancel_type = callback.data.replace("cancel_", "")
    await state.clear()
    await callback.message.edit_text(f"❌ Синхронизация отменена.")
    logger.info(f"Синхронизация ({cancel_type}) отменена")

@router.message(F.text=="Синхронизировать расписание")
async def show_sync_menu(message: Message):
    """
    Обработчик команды кнопки "Синхронизировать расписание".

    Логика:
    1. Пользователь (админ) нажимает кнопку "Синхронизировать расписание".
    2. Бот отвечает сообщением "Выберите" и показывает клавиатуру
       для выбора вида синхронизации.

    Аргументы:
    message : aiogram.types.Message
        Сообщение от пользователя (админа).
    """
    await message.answer(text="Выберите режим синхронизации:", reply_markup=get_type_sync_kb())

# @router.callback_query()
# async def debug_callback(callback: CallbackQuery, state: FSMContext):
#     """Обработчик для отладки - ловит все callback_data"""
#     current_state = await state.get_state()
#     logger.info(f"Callback data: {callback.data}, Current state: {current_state}")
#     await callback.message.answer(f"Получен callback: {callback.data}, состояние: {current_state}")


@router.callback_query(F.data=="sync_university")
async def sync_all_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SyncStates.confirm_full_sync)

    await callback.message.edit_text(
        "Отправьте 'Да' для подтверждение синхронизации.",
        reply_markup=get_cancel_kb("sync_university")
    )

@router.message(StateFilter(SyncStates.confirm_full_sync))
async def confirm_full_sync(message: Message, state: FSMContext):
    """Синхронизация всего университета"""
    if message.text.strip().lower() != "да":
        await message.answer("Синхронизация для всего университета отменена.")
        await state.clear()
        return

    bot = message.bot
    text_start = "⏳ Синхронизация расписания для всех факультетов и групп..."

    try:
        sent_msg = await message.answer(text=text_start)
        await send_chat_info_log(bot, text_start)
        logger.info(text_start)

        await run_full_sync()

        text_end = "✅ Синхронизация расписания завершена для всего университета."
        await sent_msg.edit_text(text=text_end)
        await send_chat_info_log(bot, text_end)
        logger.info(text_end)
    except Exception as e:
        await message.answer(f"❌ Ошибка при синхронизации расписания для всего университета")
        logger.error(f"❌ Ошибка при синхронизации расписания для всего университета: {e}")

    await state.clear()

@router.callback_query(F.data=="sync_faculty")
async def sync_faculty_handler(callback: CallbackQuery, state: FSMContext):
    """Начало синхронизации факультета - выбор факультета"""
    try:
        await callback.message.edit_text(
            "Выберите факультет для синхронизации:",
            reply_markup=faculty_keyboard
        )
        await state.set_state(SyncStates.sync_faculty)
    except Exception as e:
        logger.error(f"Ошибка в sync_faculty_handler: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(StateFilter(SyncStates.sync_faculty), F.data.startswith("faculty:"))
async def sync_faculty_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбранного факультета для синхронизации"""
    try:
        faculty_name = abbr_faculty[callback.data.split(":")[1]]
        await callback.message.edit_text(f"⏳ Синхронизация факультета {faculty_name}...")

        await run_full_sync_for_faculty(faculty_name)

        await callback.message.edit_text(f"✅ Синхронизация завершена для факультета {faculty_name}.")
        await state.clear()
    except Exception as e:
        error_text = f"❌ Ошибка при синхронизации факультета: {str(e)}"
        await callback.message.edit_text(text=error_text)
        logger.error(error_text)
        await state.clear()

@router.callback_query(F.data == "sync_group")
async def sync_group_start(callback: CallbackQuery, state: FSMContext):
    """Начало синхронизации группы - выбор факультета"""
    try:
        await callback.message.edit_text(
            "Выберите факультет:",
            reply_markup=faculty_keyboard
        )
        await state.set_state(SyncStates.sync_group_faculty)
    except Exception as e:
        logger.error(f"Ошибка в sync_group_start: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте снова.")


@router.callback_query(StateFilter(SyncStates.sync_group_faculty), F.data.startswith("faculty:"))
async def sync_group_select_faculty(callback: CallbackQuery, state: FSMContext):
    """Выбор группы для синхронизации после выбора факультета"""
    try:
        faculty_name = abbr_faculty[callback.data.split(":")[1]]
        groups_kb = faculty_keyboards.get(faculty_name)

        if not groups_kb:
            await callback.message.edit_text("❌ Для этого факультета нет групп.")
            await state.clear()
            return

        await callback.message.edit_text(
            f"Выберите группу факультета {faculty_name}:",
            reply_markup=groups_kb
        )
        await state.set_state(SyncStates.sync_group_select)
    except Exception as e:
        logger.error(f"Ошибка в sync_group_select_faculty: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте снова.")
        await state.clear()


@router.callback_query(StateFilter(SyncStates.sync_group_select), F.data.startswith("group:"))
async def sync_group_selected(callback: CallbackQuery, state: FSMContext):
    """Синхронизация выбранной группы"""
    try:
        group_name = callback.data.split(":")[1]
        await callback.message.edit_text(f"⏳ Синхронизация расписания для группы {group_name}...")

        await run_full_sync_for_group(group_name)

        await callback.message.edit_text(f"✅ Синхронизация завершена для группы {group_name}.")
        await state.clear()
    except Exception as e:
        await callback.message.edit_text(text=f"❌ Ошибка при синхронизации группы:")
        logger.error(f"❌ Ошибка при синхронизации группы: {e}")
        await state.clear()