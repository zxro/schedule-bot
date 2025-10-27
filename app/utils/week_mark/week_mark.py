import asyncio
import logging
import math
from datetime import datetime, timedelta

from app.utils.custom_logging.TelegramLogHandler import send_chat_info_log

logger = logging.getLogger(__name__)

WEEK_MARK_STICKER = None
WEEK_MARK_TXT = None

def get_monday(date):
    """Находит понедельник для заданной даты"""
    day_of_week = date.weekday()  # 0=понедельник, ..., 6=воскресенье
    return date - timedelta(days=day_of_week)


def days_difference(date1, date2):
    """Разница в днях между двумя датами"""
    date1 = date1.replace(hour=0, minute=0, second=0, microsecond=0)
    date2 = date2.replace(hour=0, minute=0, second=0, microsecond=0)
    difference = date2 - date1
    return math.ceil(difference.total_seconds() / (24 * 60 * 60))


def is_even_week():
    """Определяет, четная ли текущая учебная неделя.

    Логика:
    - Первая учебная неделя начинается с ближайшего понедельника **после 1 сентября**.
    - Первая неделя считается **нечётной ("-")**.
    - Чётность определяется по количеству полных недель от первого понедельника.
    """
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_monday = get_monday(now)

    # Определяем учебный год
    academic_year = now.year if now.month >= 9 else now.year - 1
    september_1st = datetime(academic_year, 9, 1)

    days_to_next_monday = (7 - september_1st.weekday()) % 7
    first_monday = september_1st + timedelta(days=days_to_next_monday)

    # Если текущая неделя до начала учебного года — сдвигаем на прошлый учебный год
    if current_monday < first_monday:
        academic_year -= 1
        september_1st = datetime(academic_year, 9, 1)
        days_to_next_monday = (7 - september_1st.weekday()) % 7
        first_monday = september_1st + timedelta(days=days_to_next_monday)

    # Считаем количество недель между текущей неделей и первой учебной
    weeks_diff = (current_monday - first_monday).days // 7

    # Первая неделя ("-") считается нечётной, поэтому:
    return weeks_diff % 2 == 0  # True -> чётная ("-"), False -> нечётная ("+")


def get_week_mark():
    """Возвращает маркер недели"""
    return ("➖", "minus") if is_even_week() else ("➕", "plus")


async def update_week_mark():
    """Фоновая задача: обновляет WEEK_MARK каждый понедельник в 00:00"""
    global WEEK_MARK_STICKER
    global WEEK_MARK_TXT

    while True:
        WEEK_MARK_STICKER, WEEK_MARK_TXT = get_week_mark()
        txt = f"Обновлён маркер недели: {WEEK_MARK_STICKER}"
        logger.info(txt)
        await send_chat_info_log(txt)

        now = datetime.now()

        days_until_monday = (0 - now.weekday()) % 7
        next_monday = now + timedelta(days=days_until_monday)
        next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)

        if next_monday <= now:
            next_monday += timedelta(days=7)

        sleep_time = (next_monday - now).total_seconds()
        await asyncio.sleep(sleep_time)


async def init_week_mark():
    """Вызывается при старте бота для начальной инициализации WEEK_MARK"""
    global WEEK_MARK_TXT
    global WEEK_MARK_STICKER
    WEEK_MARK_STICKER, WEEK_MARK_TXT = get_week_mark()