from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

from app.keyboards.admin_kb import get_admin_kb


def start_keyboard():
    """
    @brief Создает клавиатуру для главного меню после команды /start.

    @details: Возвращает клавиатуру с кнопкой "Получить расписание курса"

    @return ReplyKeyboardMarkup: Объект клавиатуры для отправки пользователю.
    """

    """
    ВРЕМЕННО возвращает админ клавиатуру
    """

    return get_admin_kb()