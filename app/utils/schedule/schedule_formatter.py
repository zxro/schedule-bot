import re
from collections import defaultdict

MAX_MESSAGE_LENGTH = 4000

lesson_num_emoji = {
    0: "1️⃣", 1: "2️⃣", 2: "3️⃣",
    3: "4️⃣", 4: "5️⃣", 5: "6️⃣", 6: "7️⃣"
}

weekday_names = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье"
}

lessonTimeData = {
    0: {0: "08:30", 1: "10:05"},
    1: {0: "10:15", 1: "11:50"},
    2: {0: "12:10", 1: "13:45"},
    3: {0: "14:00", 1: "15:35"},
    4: {0: "15:55", 1: "17:30"},
    5: {0: "17:45", 1: "19:20"},
    6: {0: "19:30", 1: "21:00"}
}

url_pattern = re.compile(r"(https?://\S+)")


def escape_md_v2(text: str):
    """
    Экранирует спецсимволы MarkdownV2.

    Параметры:
        text (str): Исходный текст.
    Возвращает:
        str: Текст с добавленными обратными слэшами перед спецсимволами.
    """

    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)


def _get_lesson_time(lesson_number):
    """
    Возвращает время начала и конца пары по её номеру.

    Параметры:
        lesson_number (int): Номер пары (0–6).
    Возвращает:
        tuple[str, str]: (время_начала, время_конца)
    """

    if lesson_number in lessonTimeData:
        lesson = lessonTimeData[lesson_number]
        return lesson[0], lesson[1]
    else:
        return "❓❓:❓❓", "❓❓:❓❓"


def _filter_lessons_by_week(lessons, week: str):
    """
    Фильтрация пар по типу недели.

    Параметры:
        lessons (list): Список объектов Lesson.
        week (str): "plus" | "minus" | "full".
    Возвращает:
        list: Отфильтрованный список занятий.
    """

    if week == "plus":
        return [l for l in lessons if l.week_mark in ("plus", "every", None)]
    elif week == "minus":
        return [l for l in lessons if l.week_mark in ("minus", "every", None)]
    else:
        return lessons[:]  # "full" — без фильтра


def _create_lessons_by_day(filtered_lessons):
    """
    Группировка пар по дням недели.

    Параметры:
        filtered_lessons (list): Список отфильтрованных занятий.
    Возвращает:
        dict[int, list]: Ключ — номер дня недели, значение — список занятий.
    """

    lessons_by_day = defaultdict(list)
    for l in filtered_lessons:
        if l.weekday is not None:
            lessons_by_day[l.weekday].append(l)
    return lessons_by_day


def _build_schedule_messages(lessons_by_day, format_lesson_func, header: str):
    """
    Разбивает расписание на несколько сообщений (если текст слишком длинный).

    Параметры:
        lessons_by_day (dict): Сгруппированные по дням занятия.
        format_lesson_func (Callable): Функция форматирования одной пары.
        header (str): Заголовок расписания.
    Возвращает:
        list[str]: Список готовых сообщений.
    """

    day_texts = []
    for wd in sorted(lessons_by_day.keys()):
        day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)
        day_block = f"🗓 *{escape_md_v2(weekday_names[wd])}*:\n" + "\n\n".join(
            format_lesson_func(l) for l in day_lessons) + "\n\n\n"
        day_texts.append(day_block)

    messages = []
    current_text = header
    for day_text in day_texts:
        if len(current_text) + len(day_text) > MAX_MESSAGE_LENGTH:
            messages.append(current_text)
            current_text = day_text
        else:
            current_text += day_text
    if current_text:
        messages.append(current_text)

    return messages


def _get_header(header_prefix: str, week: str):
    """
    Формирует заголовок расписания в зависимости от типа недели.

    Параметры:
        header_prefix (str): Префикс заголовка
        week (str): Тип недели ("plus", "minus", "full").
    Возвращает:
        str: Текст заголовка в MarkdownV2.
    """

    header_prefix = f"*{escape_md_v2(header_prefix)}*"
    return {
        "plus": f"{header_prefix} ➕\n\n",
        "minus": f"{header_prefix} ➖\n\n",
        "full": f"{header_prefix}\n\n"
    }.get(week, f"{header_prefix}\n\n")


def _format_common_lesson_data(l):
    """
    Форматирует общие данные пары (номер, время, предмет, аудитория).

    Параметры:
        l (Lesson): Объект занятия.
    Возвращает:
        tuple[str, str, str, str, str]:
            (week_marker, emoji_номер, предмет, аудитория, время)
    """

    start, end = _get_lesson_time(lesson_number=l.lesson_number)
    time_str = f"⏳ {start} \\- {end}"

    lesson_num = lesson_num_emoji.get(l.lesson_number, "❓")

    rooms_text = l.rooms or "Место проведения не указано"
    urls = url_pattern.findall(rooms_text)
    if urls:
        rooms_text = url_pattern.sub(lambda m: f"[нажмите для подключения]({m.group(0)})", rooms_text)
    else:
        rooms_text = escape_md_v2(rooms_text)
    room = f"📍{rooms_text}"

    subject = escape_md_v2(l.subject or "Предмет не указан")

    # убран - ⚪
    marker = {"plus": "➕", "minus": "➖", "every": ""}.get(l.week_mark or "every", "")

    return marker, lesson_num, subject, room, time_str


def format_schedule_students(lessons, week: str, header_prefix: str = "📅 Расписание"):
    """
    Форматирование расписания для студентов.

    Параметры:
        lessons (list): Список объектов Lesson.
        week (str): Тип недели ("plus", "minus", "full").
        header_prefix (str): Префикс заголовка расписания.
    Возвращает:
        list[str]: Список отформатированных текстов сообщений в MarkdownV2.
    """

    filtered_lessons = _filter_lessons_by_week(lessons, week)
    if not filtered_lessons:
        return []

    def format_lesson(l):
        marker, lesson_num, subject, room, time_str = _format_common_lesson_data(l)

        professors = ", ".join(l.professors) if isinstance(l.professors, list) else (
                    l.professors or "Преподаватель не указан")
        professors = escape_md_v2(professors)

        return f"  {lesson_num} {marker} {subject}\n  👨‍🏫 {professors}\n  {room}\n  {time_str}"

    lessons_by_day = _create_lessons_by_day(filtered_lessons)
    header = _get_header(header_prefix, week)

    return _build_schedule_messages(lessons_by_day, format_lesson, header)


def format_schedule_professor(lessons, week: str, header_prefix: str = "📅 Расписание преподавателя"):
    """
    Форматирование расписания преподавателя.

    Параметры:
        lessons (list): Список объектов ProfessorLesson.
        week (str): Тип недели ("plus", "minus", "full").
        header_prefix (str): Префикс заголовка расписания.
    Возвращает:
        list[str]: Список отформатированных сообщений в MarkdownV2.
    """

    filtered_lessons = _filter_lessons_by_week(lessons, week)
    if not filtered_lessons:
        return []

    def format_lesson(l):
        marker, lesson_num, subject, room, time_str = _format_common_lesson_data(l)
        urls = url_pattern.findall(room)
        if urls:
            room = "📍Онлайн"
        return f"  {lesson_num} {marker} {subject}\n  {room}\n  {time_str}"

    lessons_by_day = _create_lessons_by_day(filtered_lessons)
    header = _get_header(header_prefix, week)

    return _build_schedule_messages(lessons_by_day, format_lesson, header)