"""
Реализует обработчики (aiogram Router) для синхронизации расписания администратором.

- Синхронизация всего университета
- Синхронизация отдельного факультета
- Синхронизация отдельной группы
- Возможность отмены синхронизации на любом этапе

- Информация отправляется в Telegram через send_chat_info_log
- Ошибки фиксируются через logging.error
"""
import asyncio

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import logging

from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log
from app.utils.schedule.worker import run_full_sync_for_group, run_full_sync, run_full_sync_for_faculty
from app.keyboards.base_kb import abbr_faculty
from app.keyboards.sync_kb import get_type_sync_kb, refresh_sync_keyboards
import app.keyboards.sync_kb as sync_kb

from app.state.states import SyncStates

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("cancel_"), F.data.endswith("_sync"))
async def cancel_sync(callback: CallbackQuery, state: FSMContext):
    """
    Обработка отмены синхронизации.

    Действия:
    - Очищает состояние.
    - Сообщает пользователю об отмене.
    - Логирует событие.
    """

    cancel_type = callback.data.replace("cancel_", "")
    await state.clear()
    await callback.message.edit_text(f"❌ Синхронизация отменена.")
    logger.info(f"Синхронизация ({cancel_type}) отменена")
    await asyncio.sleep(1)
    await callback.message.delete()

@router.callback_query(F.data=="sync_schedule")
async def show_sync_menu(callback: CallbackQuery):
    """
    Стартовый обработчик синхронизации.

    Действия:
    - Отправляет пользователю клавиатуру выбора режима синхронизации
      (университет, факультет, группа).
    """
    await callback.message.edit_text(text="Выберите режим синхронизации:", reply_markup=get_type_sync_kb())

@router.callback_query(F.data=="sync_university")
async def sync_all_handler(callback: CallbackQuery, state: FSMContext):
    """
    Начало сценария синхронизации всего университета.

    - Просит подтверждение у пользователя.
    - Устанавливает состояние confirm_full_sync.
    """

    await state.set_state(SyncStates.confirm_full_sync)
    await state.update_data(confirm_message_id=callback.message.message_id)

    kb_cancel = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_university_sync")]
        ]
    )

    await callback.message.edit_text(
        "Отправьте 'Да' для подтверждение синхронизации.",
        reply_markup=kb_cancel
    )

@router.message(StateFilter(SyncStates.confirm_full_sync))
async def confirm_full_sync(message: Message, state: FSMContext):
    """
    Выполняет синхронизацию расписания для всего университета.

    Действия:
    - Проверяет подтверждение ("да").
    - Запускает run_full_sync().
    - Логирует начало и завершение синхронизации.
    - Обрабатывает ошибки.
    """

    data = await state.get_data()
    confirm_message_id = data.get('confirm_message_id')

    if confirm_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=confirm_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с подтверждением: {e}")

    if message.text.strip().lower() != "да":
        await message.answer("Синхронизация для всего университета отменена.")
        logger.info("Синхронизация для всего университета отменена.")
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
        text_err = "❌ Ошибка при синхронизации расписания для всего университета"
        await message.answer(text_err)
        logger.error(f"{text_err}: {e}")

    await state.clear()

@router.callback_query(F.data=="sync_faculty")
async def sync_faculty_handler(callback: CallbackQuery, state: FSMContext):
    """
    Начало сценария синхронизации факультета.

    - Показывает клавиатуру с факультетами.
    - Устанавливает состояние sync_faculty.
    """

    try:
        await callback.message.edit_text(
            "Выберите факультет для синхронизации:",
            reply_markup=sync_kb.faculty_keyboard_sync
        )
        await state.set_state(SyncStates.sync_faculty)
    except Exception as e:
        logger.error(f"Ошибка в sync_faculty_handler: {e}")
        await callback.message.answer("❌ Ошибка при синхронизации расписания для факультета")


@router.callback_query(StateFilter(SyncStates.sync_faculty), F.data.startswith("faculty:"))
async def sync_faculty_selected(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор факультета.

    - Запускает синхронизацию факультета.
    - Сообщает о завершении.
    - Логирует процесс.
    """

    faculty_name = abbr_faculty[callback.data.split(":")[1]]
    try:
        await callback.message.edit_text(f"⏳ Синхронизация факультета {faculty_name}...")

        await run_full_sync_for_faculty(faculty_name)

        await callback.message.edit_text(f"✅ Синхронизация завершена для факультета {faculty_name}.")
        await state.clear()
    except Exception as e:
        await callback.message.edit_text(text=f"❌ Ошибка при синхронизации факультета.")
        logger.error(f"❌ Ошибка при синхронизации факультета {faculty_name}: {e}")
        await state.clear()

@router.callback_query(F.data == "sync_group")
async def sync_group_start(callback: CallbackQuery, state: FSMContext):
    """
    Начало сценария синхронизации группы.

    - Сначала выбирается факультет.
    - Устанавливается состояние sync_group_faculty.
    """

    try:
        await callback.message.edit_text(
            "Выберите факультет:",
            reply_markup=sync_kb.faculty_keyboard_sync
        )
        await state.set_state(SyncStates.sync_group_faculty)
        await refresh_sync_keyboards()
    except Exception as e:
        logger.error(f"Ошибка в sync_group_start: {e}")
        await callback.message.answer("❌ Ошибка при синхронизации расписания для группы.")

@router.callback_query(StateFilter(SyncStates.sync_group_faculty), F.data.startswith("faculty:"))
async def sync_group_select_faculty(callback: CallbackQuery, state: FSMContext):
    """
    После выбора факультета — показывает группы этого факультета.

    - Если групп нет -> сообщение об ошибке.
    - Если группы есть ->клавиатура с группами.
    """

    try:
        faculty_name = abbr_faculty[callback.data.split(":")[1]]
        groups_kb = sync_kb.groups_keyboards_sync.get(faculty_name)

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
        await callback.message.answer("❌ Ошибка при синхронизации расписания для группы.")
        await state.clear()


@router.callback_query(StateFilter(SyncStates.sync_group_select), F.data.startswith("group:"))
async def sync_group_selected(callback: CallbackQuery, state: FSMContext):
    """
    Выполняет синхронизацию для выбранной группы.

    - Запускает run_full_sync_for_group().
    - Сообщает о завершении.
    - Обрабатывает ошибки.
    """

    group_name = callback.data.split(":")[1]
    try:
        await callback.message.edit_text(f"⏳ Синхронизация расписания для группы {group_name}...")

        await run_full_sync_for_group(group_name)

        await callback.message.edit_text(f"✅ Синхронизация завершена для группы {group_name}.")
        await state.clear()
    except Exception as e:
        await callback.message.edit_text(text=f"❌ Ошибка при синхронизации расписания для группы: {group_name}")
        logger.error(f"❌ Ошибка при синхронизации группы: {e}")
        await state.clear()