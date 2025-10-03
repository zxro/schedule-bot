from aiogram import Router, types, F
from app.keyboards.courses import choose_course_keyboard
from app.database.database import Database
from aiogram.exceptions import TelegramBadRequest

router = Router()


@router.message(F.text == "Получить расписание курса")
async def select_course(message: types.Message):
    """
    Обработчик нажатия кнопки "Получить расписание курса".

    Отправляет inline-клавиатуру с выбором курса.

    Аргументы:
        message (types.Message): Объект сообщения Telegram.
    """
    await message.answer(text="Выберите курс:", reply_markup=choose_course_keyboard())


@router.callback_query(F.data.startswith("course_"))
async def handle_course_choice(callback: types.CallbackQuery, db: Database):
    """
    Обработчик нажатия кнопки выбора курса.

    Аргументы:
        callback (types.CallbackQuery): Объект callback-запроса.
        db (Database): Объект для работы с базой данных.

    Действия:
        - Извлекает номер курса из callback_data
        - Получает расписание из БД
        - Форматирует и отправляет расписание
    """
    course_number = int(callback.data.split("_")[1])

    # Показываем уведомление о загрузке
    await callback.answer(f"Загружаем расписание {course_number} курса...")

    try:
        # Получаем расписание из БД
        schedule = await db.get_schedule_by_course(course_number)

        if not schedule:
            await callback.message.answer(f"📭 Расписание для {course_number} курса не найдено.")
            return

        # Форматируем расписание
        schedule_text = format_schedule(schedule, course_number)

        # Отправляем расписание
        await callback.message.answer(schedule_text)

    except Exception as e:
        await callback.message.answer("❌ Произошла ошибка при загрузке расписания.")
        print(f"Ошибка при получении расписания: {e}")


def format_schedule(schedule: list, course: int) -> str:
    """
    Форматирует список занятий в читаемый текст

    Аргументы:
        schedule: Список объектов ScheduleItem
        course: Номер курса

    Возвращает:
        str: Отформатированное расписание
    """
    if not schedule:
        return f"📭 Расписание для {course} курса не найдено."

    result = f"📚 Расписание {course} курса:\n\n"

    current_day = ""
    for item in schedule:
        if item.day_of_week != current_day:
            current_day = item.day_of_week
            result += f"\n📅 **{current_day.capitalize()}**:\n"

        time_str = f"{item.time_start.strftime('%H:%M')}-{item.time_end.strftime('%H:%M')}"
        classroom_str = f" (ауд. {item.classroom})" if item.classroom else ""

        result += f"🕒 {time_str} - {item.subject}\n"
        result += f"   👨‍🏫 {item.teacher}{classroom_str}\n"

    return result