from aiogram import Router, types, F
from app.keyboards.courses import choose_course_keyboard

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
async def handle_course_choice(callback: types.CallbackQuery):
    """
    Обработчик нажатия кнопки выбора курса.

    Аргументы:
        callback (types.CallbackQuery): Объект callback-запроса.

    Действия:
        - Извлекает номер курса из callback_data
        - Отправляет всплывающее уведомление о выбранном курсе
    """

    course_number = callback.data.split("_")[1]
    # Логика обработки выбранного курса
    await callback.answer(f"Вы выбрали курс: {course_number}")
