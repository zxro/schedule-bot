from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

def start_keyboard():
    """
    @brief Создает клавиатуру для главного меню после команды /start.

    @details: Возвращает клавиатуру с кнопкой "Получить расписание курса"

    @return ReplyKeyboardMarkup: Объект клавиатуры для отправки пользователю.
    """

    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="Запустить синхронизацию"))
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)