"""
Реализует обработчики (aiogram Router) для просмотра расписания студентами.

1. Выбор факультета
2. Выбор группы
3. Выбор типа недели (чётная, нечётная, полное)
4. Форматирование и вывод расписания

Ошибки при формировании расписания фиксируются через logging.
"""

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.utils import week_mark
from app.utils.schedule.worker import get_schedule_for_group
from app.keyboards.faculty_kb import abbr_faculty
from app.keyboards.find_kb import faculty_keyboard_find, groups_keyboards_find
from app.keyboards.schedule_kb import choice_week_kb
from app.state.states import ShowSheduleStates
from app.utils.schedule.schedule_formatter import escape_md_v2, format_schedule

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

@router.message(F.text=="Другие расписания")
async def other_schedules(message: Message, state: FSMContext):
    pass

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

    await callback.message.edit_text(f"Выберите тип расписания:\n"
                                     f"Сейчас неделя {week_mark.WEEK_MARK_STICKER}", reply_markup=choice_week_kb())

@router.callback_query(StateFilter(ShowSheduleStates.choice_week), F.data.startswith("week:"))
async def show_schedule(callback: CallbackQuery, state: FSMContext):
    """
    Показывает расписание для выбранной группы и типа недели
    (чётная, нечётная, полное) с использованием общей функции форматирования.
    """

    state_data = await state.get_data()
    group_name = state_data.get("group_name")
    week = callback.data.split(":")[1]

    try:
        lessons = await get_schedule_for_group(group_name)
        if not lessons:
            await callback.message.edit_text(f"Расписание для {group_name} пустое.")
            return

        messages = format_schedule(lessons=lessons, week=week, header_prefix=f"📅 Расписание для *{escape_md_v2(group_name)}*")

        if not messages:
            await callback.message.edit_text(f"На выбранную неделю ({week}) расписание для {group_name} пустое.")
            return

        await callback.message.edit_text(messages[0], parse_mode="MarkdownV2")
        for msg in messages[1:]:
            await callback.message.answer(msg.strip(), parse_mode="MarkdownV2")

    except Exception as e:
        logger.exception(f"Ошибка при выводе расписания для {group_name}: {e}")
        await callback.message.edit_text(
            f"⚠️ Произошла ошибка при выводе расписания для *{escape_md_v2(group_name)}*.",
            parse_mode="MarkdownV2"
        )

# @router.callback_query(StateFilter(ShowSheduleStates.choice_week), F.data.startswith("week:"))
# async def show_schedule(callback: CallbackQuery, state: FSMContext):
#     MAX_MESSAGE_LENGTH = 4000
#     url_pattern = re.compile(r"(https?://\S+)")
#
#
#     state_data = await state.get_data()
#     group_name = state_data.get("group_name")
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
#         lesson_num_emoji = {
#             1: "1️⃣", 2: "2️⃣", 3: "3️⃣",
#             4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣"
#         }
#
#         def format_lesson(l):
#             start = l.start_time.strftime("%H:%M") if l.start_time else "❓❓:❓❓"
#             end = l.end_time.strftime("%H:%M") if l.end_time else "❓❓:❓❓"
#             time_str = f"⏳ {start} \\- {end}"
#
#             lesson_num = lesson_num_emoji.get(l.lesson_number + 1, "❓")
#
#             rooms_text = l.rooms or "Место проведения не указано"
#             urls = url_pattern.findall(rooms_text)
#             if urls:
#                 rooms_text = url_pattern.sub(lambda m: f"[нажмите для подключения]({m.group(0)})", rooms_text)
#             else:
#                 rooms_text = escape_md_v2(rooms_text)
#             room = f"📍{rooms_text}"
#
#             professors = ", ".join(l.professors) if isinstance(l.professors, list) else (l.professors or "Преподаватель не указан")
#             professors = escape_md_v2(professors)
#
#             marker = "⚪"
#             if l.week_mark == "plus":
#                 marker = "➕"
#             elif l.week_mark == "minus":
#                 marker = "➖"
#
#             subject = escape_md_v2(l.subject or "Предмет не указан")
#
#             return f"  {marker} {lesson_num} {subject}\n  👨‍🏫 {professors}\n  {room}\n  {time_str}"
#
#         day_texts = []
#         header = {
#             "plus": "📅 Неделя ➕\n\n",
#             "minus": "📅 Неделя ➖\n\n",
#             "full": "📅 Полное расписание:\n\n"
#         }.get(week, "📅 Полное расписание:\n\n")
#
#         for wd in week_order:
#             day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)
#             if week == "plus":
#                 filtered = [l for l in day_lessons if l.week_mark in ("every", "plus")]
#             elif week == "minus":
#                 filtered = [l for l in day_lessons if l.week_mark in ("every", "minus")]
#             else:
#                 filtered = day_lessons
#
#             if filtered:
#                 day_block = f"🗓 *{escape_md_v2(weekday_names[wd])}*:\n" + "\n\n".join(format_lesson(l) for l in filtered) + "\n\n"
#                 day_texts.append(day_block)
#
#         if not day_texts:
#             await callback.message.edit_text(f"На выбранную неделю ({week}) расписание для {group_name} пустое.")
#             return
#
#         messages = []
#         current_text = header
#         for day_text in day_texts:
#             if len(current_text) + len(day_text) > MAX_MESSAGE_LENGTH:
#                 messages.append(current_text)
#                 current_text = day_text
#             else:
#                 current_text += day_text
#         if current_text:
#             messages.append(current_text)
#
#         await callback.message.edit_text(messages[0], parse_mode="MarkdownV2")
#         for msg in messages[1:]:
#             await callback.message.answer(msg, parse_mode="MarkdownV2")
#
#     except Exception as e:
#         await callback.message.edit_text(f"Ошибка при выводе расписания для {group_name}")
#         logger.error(f"Ошибка при выводе расписания для {group_name}: {e}")