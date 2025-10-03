from aiogram import Router, types, F
from app.keyboards.courses import choose_course_keyboard

router = Router()

@router.message(F.text == "Получить расписание курса")
async def select_course(message: types.Message):
    """
    @brief Обработчик нажатия кнопки "Получить расписание курса".

    @details Отправляет inline-клавиатуру с выбором курса.

    @param message (types.Message): Объект сообщения Telegram.
    """

    await message.answer(text="Выберите курс:", reply_markup=choose_course_keyboard())


@router.callback_query(F.data.startswith("course_"))
async def handle_course_choice(callback: types.CallbackQuery):
    """
    @brief Обработчик нажатия кнопки выбора курса.

    @details
        - Извлекает номер курса из callback_data
        - Отправляет всплывающее уведомление о выбранном курсе

    @param callback (types.CallbackQuery): Объект callback-запроса.
    """

    course_number = callback.data.split("_")[1]
    # Логика обработки выбранного курса
    await callback.answer(f"Вы выбрали курс: {course_number}")
