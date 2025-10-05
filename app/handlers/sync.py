"""
Реализует обработчики (aiogram Router) для синхронизации расписания администратором.

- Синхронизация всего университета
- Синхронизация отдельного факультета
- Синхронизация отдельной группы
- Возможность отмены синхронизации на любом этапе

- Информация отправляется в Telegram через send_chat_info_log
- Ошибки фиксируются через logging.error
"""

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

@router.message(F.text=="Синхронизировать расписание")
async def show_sync_menu(message: Message):
    """
    Стартовый обработчик синхронизации.

    Действия:
    - Отправляет пользователю клавиатуру выбора режима синхронизации
      (университет, факультет, группа).
    """
    await message.answer(text="Выберите режим синхронизации:", reply_markup=get_type_sync_kb())

@router.callback_query(F.data=="sync_university")
async def sync_all_handler(callback: CallbackQuery, state: FSMContext):
    """
    Начало сценария синхронизации всего университета.

    - Просит подтверждение у пользователя.
    - Устанавливает состояние confirm_full_sync.
    """

    await state.set_state(SyncStates.confirm_full_sync)

    await callback.message.edit_text(
        "Отправьте 'Да' для подтверждение синхронизации.",
        reply_markup=get_cancel_kb("sync_university")
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
    """
    Начало сценария синхронизации факультета.

    - Показывает клавиатуру с факультетами.
    - Устанавливает состояние sync_faculty.
    """

    try:
        await callback.message.edit_text(
            "Выберите факультет для синхронизации:",
            reply_markup=faculty_keyboard
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
        error_text = f"❌ Ошибка при синхронизации факультета: {str(e)}"
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
            reply_markup=faculty_keyboard
        )
        await state.set_state(SyncStates.sync_group_faculty)
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