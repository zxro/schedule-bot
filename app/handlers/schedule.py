"""
Реализует обработчики (aiogram Router) для просмотра расписания студентами.

1. Выбор факультета
2. Выбор группы
3. Выбор типа недели (чётная, нечётная, полное)
4. Форматирование и вывод расписания

Ошибки при формировании расписания фиксируются через logging.
"""

import logging
from collections import defaultdict

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.extracting_schedule.worker import get_schedule_for_group
from app.keyboards.faculty_kb import abbr_faculty
from app.keyboards.find_kb import faculty_keyboard_find, groups_keyboards_find
from app.keyboards.schedule_keyboards import choice_week_kb
from app.state.states import ShowSheduleStates

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("cancel_"), F.data.endswith("_find"))
async def cancel_find(callback: CallbackQuery, state: FSMContext):
    """
    Обработка отмены поиска.

    Действия:
    - Очищает состояние.
    - Сообщает пользователю об отмене.
    """

    await state.clear()
    await callback.message.edit_text(f"❌ Поиск отменён.")

@router.message(F.text=="Просмотреть расписание")
async def get_schedule_start(message: Message, state: FSMContext):
    """
    Начало сценария просмотра расписания.

    Действия:
    - Отправляет клавиатуру факультетов.
    - Устанавливает состояние choice_faculty.
    """

    await message.answer("Выберите факультет:", reply_markup=faculty_keyboard_find)
    await state.set_state(ShowSheduleStates.choice_faculty)

@router.callback_query(StateFilter(ShowSheduleStates.choice_faculty), F.data.startswith("faculty:"))
async def get_schedule_faculty(callback: CallbackQuery, state: FSMContext):
    """
    Обработка выбора факультета.

    Действия:
    - Определяет название факультета по сокращению.
    - Показывает клавиатуру с группами.
    - Если групп нет → сообщение об ошибке.
    """

    faculty_name = abbr_faculty[callback.data.split(":")[1]]
    groups_kb = groups_keyboards_find.get(faculty_name)
    if not groups_kb:
        await callback.message.edit_text("❌ Для этого факультета нет групп.")
        return
    await callback.message.edit_text(f"Выберите группу факультета {faculty_name}:", reply_markup=groups_kb)
    await state.set_state(ShowSheduleStates.choice_group)

@router.callback_query(StateFilter(ShowSheduleStates.choice_group), F.data.startswith("group:"))
async def choice_type_week(callback: CallbackQuery, state: FSMContext):
    """
    Обработка выбора группы.

    Действия:
    - Сохраняет выбранную группу в состояние.
    - Просит выбрать тип расписания (неделя plus/minus/full).
    """

    group_name = callback.data.split(":")[1]
    await state.update_data(group_name=group_name)
    await state.set_state(ShowSheduleStates.choice_week)

    await callback.message.edit_text("Выберите тип расписания:", reply_markup=choice_week_kb())

# @router.callback_query(StateFilter(ShowSheduleStates.choice_week), F.data.startswith("week:"))
# async def show_schedule(callback: CallbackQuery, state: FSMContext):
#     """
#     Вывод расписания для выбранной группы.
#
#     Аргументы:
#     callback : aiogram.types.CallbackQuery
#         Данные callback-кнопки.
#     state : FSMContext
#         Контекст FSM.
#
#     Логика:
#     - Загружает расписание из БД.
#     - Группирует занятия по дням.
#     - Фильтрует в зависимости от выбранной недели.
#     - Форматирует текст.
#     """
#
#     state_data = await state.get_data()
#     group_name = state_data.get("group_name")
#
#     # week: plus / minus / full
#     week = callback.data.split(":")[1]
#
#     try:
#         lessons = await get_schedule_for_group(group_name)
#         if not lessons:
#             await callback.message.edit_text(f"Расписание для {group_name} пустое.")
#             return
#
#         lessons_by_day = defaultdict(list)
#         for l in lessons:
#             if l.weekday is not None:
#                 lessons_by_day[l.weekday].append(l)
#
#         week_order = sorted(lessons_by_day.keys())
#
#         weekday_names = {
#             1: "Понедельник",
#             2: "Вторник",
#             3: "Среда",
#             4: "Четверг",
#             5: "Пятница",
#             6: "Суббота",
#             7: "Воскресенье"
#         }
#
#         def format_lesson(l):
#             lesson_num_emoji = {
#                 1: "1️⃣",
#                 2: "2️⃣",
#                 3: "3️⃣",
#                 4: "4️⃣",
#                 5: "5️⃣",
#                 6: "6️⃣",
#                 7: "7️⃣"
#             }
#
#             start = l.start_time.strftime("%H:%M") if l.start_time else "??:??"
#             end = l.end_time.strftime("%H:%M") if l.end_time else "??:??"
#             time_str = f"⏳ {start} - {end}"
#
#             lesson_num = lesson_num_emoji.get(l.lesson_number + 1, "❓") if l.lesson_number is not None else "❓"
#             room = f"📍{l.rooms}" if l.rooms else "📍Место проведения не указано"
#
#             professors = l.professors
#             if isinstance(professors, list):
#                 professors = ", ".join(professors)
#             elif not professors:
#                 professors = "Преподаватель не указан"
#
#             if l.week_mark == "plus":
#                 marker = "➕"
#             elif l.week_mark == "minus":
#                 marker = "➖"
#             else:  # every
#                 marker = "⚪"
#
#             return f"  {marker} {lesson_num} {l.subject}\n  👨‍🏫 {professors}\n  {room}\n  {time_str}"
#
#         text = ""
#         for wd in week_order:
#             day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)
#
#             if week == "plus":
#                 filtered_lessons = [l for l in day_lessons if l.week_mark in ("every", "plus")]
#                 header = "📅 Неделя ➖\n\n"
#             elif week == "minus":
#                 filtered_lessons = [l for l in day_lessons if l.week_mark in ("every", "minus")]
#                 header = "📅 Неделя ➕:\n\n"
#             else:  # full
#                 filtered_lessons = day_lessons
#                 header = "📅 Полное расписание:\n\n"
#
#             if filtered_lessons:
#                 if not text:
#                     text += header
#                 text += f"🗓 {weekday_names[wd]}:\n"
#                 text += "\n\n".join(format_lesson(l) for l in filtered_lessons) + "\n\n\n"
#
#         if not text:
#             text = f"На выбранную неделю ({week}) расписание для {group_name} пустое."
#
#         await callback.message.edit_text(text)
#
#     except Exception as e:
#         await callback.message.edit_text(f"Ошибка при выводе расписания для {group_name}")
#         logger.error(f"Ошибка при выводе расписания для {group_name}: {e}")

@router.callback_query(StateFilter(ShowSheduleStates.choice_week), F.data.startswith("week:"))
async def show_schedule(callback: CallbackQuery, state: FSMContext):
    """
    Вывод расписания для выбранной группы.

    Аргументы:
    callback : aiogram.types.CallbackQuery
        Данные callback-кнопки.
    state : FSMContext
        Контекст FSM.

    Логика:
    - Загружает расписание из БД.
    - Группирует занятия по дням.
    - Фильтрует в зависимости от выбранной недели.
    - Форматирует текст.
    - Делит сообщение на блоки если его длина больше чем MAX_MESSAGE_LENGTH
    """

    MAX_MESSAGE_LENGTH = 4000

    state_data = await state.get_data()
    group_name = state_data.get("group_name")
    week = callback.data.split(":")[1]

    try:
        lessons = await get_schedule_for_group(group_name)
        if not lessons:
            await callback.message.edit_text(f"Расписание для {group_name} пустое.")
            return

        lessons_by_day = defaultdict(list)
        for l in lessons:
            if l.weekday is not None:
                lessons_by_day[l.weekday].append(l)

        week_order = sorted(lessons_by_day.keys())
        weekday_names = {
            1: "Понедельник",
            2: "Вторник",
            3: "Среда",
            4: "Четверг",
            5: "Пятница",
            6: "Суббота",
            7: "Воскресенье"
        }

        lesson_num_emoji = {
            1: "1️⃣", 2: "2️⃣", 3: "3️⃣",
            4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣"
        }

        def format_lesson(l):
            start = l.start_time.strftime("%H:%M") if l.start_time else "❓❓:❓❓"
            end = l.end_time.strftime("%H:%M") if l.end_time else "❓❓:❓❓"
            time_str = f"⏳ {start} - {end}"

            lesson_num = lesson_num_emoji.get(l.lesson_number + 1, "❓") if l.lesson_number is not None else "❓"
            room = f"📍{l.rooms}" if l.rooms else "📍Место проведения не указано"

            professors = ", ".join(l.professors) if isinstance(l.professors, list) else (l.professors or "Преподаватель не указан")

            marker = "⚪"
            if l.week_mark == "plus":
                marker = "➕"
            elif l.week_mark == "minus":
                marker = "➖"

            return f"  {marker} {lesson_num} {l.subject}\n  👨‍🏫 {professors}\n  {room}\n  {time_str}"

        day_texts = []
        header = {
            "plus": "📅 Неделя ➖\n\n",
            "minus": "📅 Неделя ➕\n\n",
            "full": "📅 Полное расписание:\n\n"
        }.get(week, "📅 Полное расписание:\n\n")

        for wd in week_order:
            day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)
            if week == "plus":
                filtered = [l for l in day_lessons if l.week_mark in ("every", "plus")]
            elif week == "minus":
                filtered = [l for l in day_lessons if l.week_mark in ("every", "minus")]
            else:
                filtered = day_lessons

            if filtered:
                day_block = f"🗓 {weekday_names[wd]}:\n" + "\n\n".join(format_lesson(l) for l in filtered) + "\n\n"
                day_texts.append(day_block)

        if not day_texts:
            await callback.message.edit_text(f"На выбранную неделю ({week}) расписание для {group_name} пустое.")
            return

        messages = []
        current_text = header
        for day_text in day_texts:
            if len(current_text) + len(day_text) > MAX_MESSAGE_LENGTH:
                messages.append(current_text)
                current_text = day_text
            else:
                current_text += day_text
        if current_text:
            messages.append(current_text)

        await callback.message.edit_text(messages[0])
        for msg in messages[1:]:
            await callback.message.answer(msg)

    except Exception as e:
        await callback.message.edit_text(f"Ошибка при выводе расписания для {group_name}")
        logger.error(f"Ошибка при выводе расписания для {group_name}: {e}")
