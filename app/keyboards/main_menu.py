from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

def start_keyboard():
    """
    Создает клавиатуру для главного меню после команды /start.

    Кнопки:
        - "Получить расписание курса"

    Возвращает:
        ReplyKeyboardMarkup: Объект клавиатуры для отправки пользователю.
    """

    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="Получить расписание курса"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)