from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def choose_course_keyboard():
    """
    Создает inline-клавиатуру с выбором курса от 1 до 5.

    Кнопки:
        - "Курс 1", "Курс 2", ..., "Курс 5"
        Каждая кнопка содержит callback_data вида "course_<номер>"

    Возвращает:
        InlineKeyboardMarkup: Объект inline-клавиатуры для отправки пользователю.
    """

    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.add(InlineKeyboardButton(text=f"Курс {i}", callback_data=f"course_{i}"))

    kb.adjust(2)
    return kb.as_markup()