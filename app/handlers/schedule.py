import logging
from collections import defaultdict

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.extracting_schedule.worker import get_schedule_for_group
from app.keyboards.faculty_kb import faculty_keyboard, faculty_keyboards, abbr_faculty
from app.keyboards.schedule_keyboards import choice_week_kb
from app.state.states import ShowSheduleStates

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text=="Просмотреть расписание")
async def get_schedule_start(message: Message, state: FSMContext):
    await message.answer("Выберите факультет:", reply_markup=faculty_keyboard)
    await state.set_state(ShowSheduleStates.choice_faculty)

@router.callback_query(StateFilter(ShowSheduleStates.choice_faculty), F.data.startswith("faculty:"))
async def get_schedule_faculty(callback: CallbackQuery, state: FSMContext):
    faculty_name = abbr_faculty[callback.data.split(":")[1]]
    groups_kb = faculty_keyboards.get(faculty_name)
    if not groups_kb:
        await callback.message.edit_text("❌ Для этого факультета нет групп.")
        return
    await callback.message.edit_text(f"Выберите группу факультета {faculty_name}:", reply_markup=groups_kb)
    await state.set_state(ShowSheduleStates.choice_group)

@router.callback_query(StateFilter(ShowSheduleStates.choice_group), F.data.startswith("group:"))
async def choice_type_week(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.split(":")[1]
    await state.update_data(group_name=group_name)
    await state.set_state(ShowSheduleStates.choice_week)

    await callback.message.edit_text("Выберите тип расписания:", reply_markup=choice_week_kb())

@router.callback_query(StateFilter(ShowSheduleStates.choice_week), F.data.startswith("week:"))
async def show_schedule(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик вывода расписания группы пользователю в зависимости от выбранной недели.
    """
    state_data = await state.get_data()
    group_name = state_data.get("group_name")

    # week: plus / minus / full
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

        def format_lesson(l):
            start = l.start_time.strftime("%H:%M") if l.start_time else "??:??"
            end = l.end_time.strftime("%H:%M") if l.end_time else "??:??"
            lesson_num = l.lesson_number if l.lesson_number else "?"
            room = l.rooms if l.rooms else "Место проведения не указано"

            if l.week_mark == "plus":
                marker = "➕"
            elif l.week_mark == "minus":
                marker = "➖"
            else:  # every
                marker = "⚪"

            return f"  {marker} {lesson_num}: {l.subject} ({room}) ({start}-{end})"

        text = ""
        for wd in week_order:
            day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)

            if week == "plus":
                filtered_lessons = [l for l in day_lessons if l.week_mark in ("every", "plus")]
                header = "📅 Плюсовая неделя:\n\n"
            elif week == "minus":
                filtered_lessons = [l for l in day_lessons if l.week_mark in ("every", "minus")]
                header = "📅 Минусовая неделя:\n\n"
            else:  # full
                filtered_lessons = day_lessons
                header = "📅 Всё расписание:\n\n"

            if filtered_lessons:
                if not text:
                    text += header
                text += f"🗓 {weekday_names[wd]}:\n"
                text += "\n".join(format_lesson(l) for l in filtered_lessons) + "\n\n"

        if not text:
            text = f"На выбранную неделю ({week}) расписание для {group_name} пустое."

        await callback.message.edit_text(text)

    except Exception as e:
        await callback.message.edit_text(f"Ошибка при выводе расписания для {group_name}")
        logger.error(f"Ошибка при выводе расписания для {group_name}: {e}")