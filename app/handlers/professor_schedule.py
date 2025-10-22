import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.database.models import Professor
from app.keyboards.schedule_kb import get_other_schedules_kb
from app.state.states import ProfessorScheduleStates
from app.utils.schedule.schedule_formatter import format_schedule_professor, escape_md_v2
from app.utils import week_mark

from app.utils.schedule.worker import get_lesson_for_professor

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки "◀️ Назад" в меню выбора расписаний.

    При вызове возвращает пользователя к начальному меню, где можно выбрать
    тип расписания для просмотра.

    Параметры:
        callback (CallbackQuery): Объект обратного вызова от Telegram, содержащий данные нажатой кнопки.
        state (FSMContext): Контекст машины состояний пользователя для управления состоянием диалога.

    Логика:
        - Изменяет текст текущего сообщения на меню выбора расписаний.
        - Устанавливает соответствующую клавиатуру.
        - Сбрасывает текущее состояние FSM.
        - Отправляет callback.answer() для подтверждения действия.
    """

    await callback.message.edit_text(
        text="Выберите расписание которое хотите посмотреть:",
        reply_markup=get_other_schedules_kb()
    )
    await callback.answer()
    await state.clear()


@router.callback_query(F.data == "professor_schedule")
async def professor_schedule(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия кнопки выбора расписания преподавателя.

    Отправляет пользователю запрос на ввод фамилии и инициалов преподавателя.
    После этого переводит FSM в состояние ожидания ввода имени.

    Параметры:
        callback (CallbackQuery): Объект callback-запроса.
        state (FSMContext): Контекст машины состояний для хранения текущего шага пользователя.

    Логика:
        - Отправляет сообщение с инструкцией по вводу имени преподавателя.
        - Устанавливает клавиатуру с кнопкой "Назад".
        - Переводит FSM в состояние `ProfessorScheduleStates.waiting_name`.
        - Сохраняет ID текущего сообщения для последующего удаления.
    """

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="cancel")]
        ])

    await callback.message.edit_text(
        text="👨‍🏫 Введите фамилию и инициалы преподавателя:\n\n"
             "Например: `Иванов И\\.И\\.`",
        reply_markup=cancel_kb,
        parse_mode="MarkdownV2"
    )
    await callback.answer()
    await state.set_state(ProfessorScheduleStates.waiting_name)
    await state.update_data(message_id_to_delete=callback.message.message_id)


@router.message(StateFilter(ProfessorScheduleStates.waiting_name))
async def waiting_name(message: Message, state: FSMContext):
    """
    Обработчик текстового ввода имени преподавателя пользователем.

    Проверяет корректность введённого имени и отображает клавиатуру с вариантами
    просмотра расписания.

    Параметры:
        message (Message): Сообщение от пользователя.
        state (FSMContext): Контекст FSM, содержащий данные, сохранённые ранее.

    Проверка:
        - Проверяет, что имя не короче 3 символов и содержит хотя бы одну букву.
        - В противном случае — сообщает об ошибке и предлагает повторить ввод.

    Логика:
        - Удаляет предыдущее сообщение, если сохранён его ID.
        - Сохраняет имя преподавателя в FSM.
        - Отправляет пользователю меню выбора типа расписания.
    """

    data = await state.get_data()
    message_id_to_delete = data.get("message_id_to_delete")
    if message_id_to_delete:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id_to_delete)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить сообщение: {e}")

    name = message.text.strip()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Professor).where(Professor.name.ilike(f"%{name}%"))
        )

    professor = result.scalars().first()
    if not professor:
        await message.answer(
            text=f"❌ Преподаватель `{name}` не найден в базе данных\\.\n\n"
                 "Проверьте написание и попробуйте снова\\.",
            reply_markup=get_other_schedules_kb(),
            parse_mode="MarkdownV2"
        )
        return

    await state.update_data(professor_name=name)

    schedule_type_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data=f"prof_today:{name}"),
            ],
            [
                InlineKeyboardButton(text="➕ Неделя", callback_data=f"prof_week_plus:{name}"),
                InlineKeyboardButton(text="➖ Неделя", callback_data=f"prof_week_minus:{name}"),
            ],
            [
                InlineKeyboardButton(text="🗓 Вся неделя", callback_data=f"prof_week_full:{name}"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="cancel")
            ]
        ]
    )

    await message.answer(
        text=f"👨‍🏫 Преподаватель: `{name}`\n\n"
             "Выберите тип расписания:",
        reply_markup=schedule_type_kb,
        parse_mode="MarkdownV2"
    )


@router.callback_query(F.data.startswith("prof_today:"))
async def handle_professor_today(callback: CallbackQuery):
    """
    Обработчик показа расписания преподавателя на текущий день.

    Извлекает фамилию преподавателя из callback data, получает его расписание,
    фильтрует занятия по текущему дню недели и отображает пользователю.

    Параметры:
        callback (CallbackQuery): Callback-запрос, содержащий имя преподавателя в формате "prof_today:Фамилия И.О.".

    Логика:
        1. Извлекает имя преподавателя и определяет текущий день недели.
        2. Получает преподавателя и его занятия с помощью `get_lesson_for_professor`.
        3. Фильтрует занятия по текущему дню и признаку недели (`plus`/`minus`/`every`).
        4. Формирует одно или несколько сообщений с расписанием.
        5. Удаляет старое сообщение и отправляет новое (или несколько, если не помещается).
        6. Обрабатывает ошибки и уведомляет пользователя об их причинах.

    Исключения:
        Exception: При ошибке загрузки или форматирования расписания.
    """

    professor_name = ""
    try:
        professor_name = callback.data.split(":")[1]
        current_weekday = datetime.now().isoweekday()

        professor, all_lessons = await get_lesson_for_professor(professor_name)

        if not professor:
            await callback.message.edit_text(f"❌ Преподаватель {professor_name} не найден.")
            await callback.answer()
            return

        if not all_lessons:
            await callback.message.edit_text(f"❌ Нет расписания для {professor_name}.")
            await callback.answer()
            return

        today_lessons = [lesson for lesson in all_lessons if lesson.weekday == current_weekday]

        current_week = week_mark.WEEK_MARK_TXT
        week_filter = "plus" if current_week == "plus" else "minus"

        filtered_lessons = [
            lesson for lesson in today_lessons
            if lesson.week_mark in (week_filter, "every", None)
        ]

        if not filtered_lessons:
            weekday_names = {
                1: "Понедельник", 2: "Вторник", 3: "Среда",
                4: "Четверг", 5: "Пятница", 6: "Суббота", 7: "Воскресенье"
            }

            new_text = (f"👨‍🏫 Расписание {escape_md_v2(professor.name)}\n"
                        f"📅 *{weekday_names[current_weekday]}*\n\n"
                        f"Сегодня пар нет\\.")

            try:
                await callback.message.edit_text(
                    text=new_text,
                    reply_markup=callback.message.reply_markup,
                    parse_mode="MarkdownV2"
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error):
                    # Игнорируем ошибку, если сообщение не изменилось
                    pass
                else:
                    raise edit_error

            await callback.answer(f"Сегодня нет пар у {professor.name}")
            return

        header_prefix = f"👨‍🏫 Расписание {professor.name} на сегодня"
        messages = format_schedule_professor(
            filtered_lessons,
            week=week_filter,
            header_prefix=header_prefix
        )

        await callback.message.delete()

        if messages:
            if len(messages) > 1:
                logger.warning(f"Расписание преподавателя {professor_name} не уместилось в одно сообщение. Проверить!!!")

            for i, msg_text in enumerate(messages):
                is_last = (i == len(messages) - 1)
                await callback.message.answer(
                    msg_text,
                    reply_markup=callback.message.reply_markup if is_last else None,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )

            await callback.answer(f"📅 Сегодня {week_mark.WEEK_MARK_STICKER}")
        else:
            await callback.message.answer("❌ Не удалось сформировать расписание.")
            await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при показе расписания на сегодня преподавателя {professor_name}: {e}.")
        await callback.message.edit_text(f"❌ Ошибка при загрузке расписания преподавателя {professor_name}")
        await callback.answer()


@router.callback_query(F.data.startswith("prof_week_"))
async def handle_professor_week(callback: CallbackQuery):
    """
    Обработчик показа расписания преподавателя на неделю.

    В зависимости от типа (➕ неделя, ➖ неделя или вся неделя)
    формирует расписание преподавателя и отправляет пользователю.

    Параметры:
        callback (CallbackQuery): Callback-запрос с данными в формате "prof_week_[тип]:Фамилия И.О.".
            Где тип может быть "plus", "minus" или "full".

    Логика:
        1. Извлекает тип недели и имя преподавателя из callback data.
        2. Получает занятия через `get_lesson_for_professor`.
        3. Форматирует расписание в зависимости от выбранного типа недели.
        4. Отправляет одно или несколько сообщений с результатом.

    Исключения:
        Exception: При ошибке загрузки или отображения расписания.
    """

    professor_name = ""
    try:
        data_parts = callback.data.split(":")
        week_type = data_parts[0].replace("prof_week_", "")
        professor_name = data_parts[1]

        professor, lessons = await get_lesson_for_professor(professor_name)

        if not professor:
            await callback.message.edit_text(f"❌ Преподаватель {professor} не найден.")
            await callback.answer()
            return

        if not lessons:
            await callback.message.edit_text(f"❌ Нет расписания для {professor_name}")
            await callback.answer()
            return

        week_names = {
            "plus": "➕ Неделя",
            "minus": "➖ Неделя",
            "full": "🗓 Вся неделя"
        }

        messages = format_schedule_professor(
            lessons,
            week=week_type,
            header_prefix=f"👨‍🏫 Расписание {professor.name} на неделю"
        )

        await callback.message.delete()

        if messages:
            if len(messages) > 1:
                logger.warning(f"Расписание преподавателя {professor_name} не уместилось в одно сообщение. Проверить!!!")

            for i, msg_text in enumerate(messages):
                is_last = (i == len(messages) - 1)
                await callback.message.answer(
                    msg_text,
                    reply_markup=callback.message.reply_markup if is_last else None,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )

            await callback.answer(week_names.get(week_type, "🗓 Неделя"))
        else:
            await callback.message.answer("❌ Не удалось сформировать расписание.")
            await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при показе расписания преподавателя {professor_name}: {e}.")
        await callback.message.edit_text(f"❌ Ошибка при загрузке расписания преподавателя {professor_name}")
        await callback.answer()