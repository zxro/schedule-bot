import re
from collections import defaultdict

MAX_MESSAGE_LENGTH = 4000

lesson_num_emoji = {
    1: "1️⃣", 2: "2️⃣", 3: "3️⃣",
    4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣"
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

url_pattern = re.compile(r"(https?://\S+)")

def escape_md_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

def format_schedule(lessons, week: str, header_prefix: str = "📅 Расписание"):
    """
    Универсальное форматирование расписания в стиле MarkdownV2.
    """

    header_prefix = f"*{escape_md_v2(header_prefix)}*"

    if week == "plus":
        filtered_lessons = [l for l in lessons if l.week_mark in ("plus", "every", None)]
    elif week == "minus":
        filtered_lessons = [l for l in lessons if l.week_mark in ("minus", "every", None)]
    else:
        filtered_lessons = lessons[:]  # "full" — без фильтра

    if not filtered_lessons:
        return []

    def format_lesson(l):
        start = l.start_time.strftime("%H:%M") if l.start_time else "❓❓:❓❓"
        end = l.end_time.strftime("%H:%M") if l.end_time else "❓❓:❓❓"
        time_str = f"⏳ {start} \\- {end}"

        lesson_num = lesson_num_emoji.get(l.lesson_number + 1, "❓")

        rooms_text = l.rooms or "Место проведения не указано"
        urls = url_pattern.findall(rooms_text)
        if urls:
            rooms_text = url_pattern.sub(lambda m: f"[нажмите для подключения]({m.group(0)})", rooms_text)
        else:
            rooms_text = escape_md_v2(rooms_text)
        room = f"📍{rooms_text}"

        professors = ", ".join(l.professors) if isinstance(l.professors, list) else (l.professors or "Преподаватель не указан")
        professors = escape_md_v2(professors)

        subject = escape_md_v2(l.subject or "Предмет не указан")

        marker = {"plus": "➕", "minus": "➖", "every": "⚪"}.get(l.week_mark or "every", "⚪")

        return f"  {marker} {lesson_num} {subject}\n  👨‍🏫 {professors}\n  {room}\n  {time_str}"

    lessons_by_day = defaultdict(list)
    for l in filtered_lessons:
        if l.weekday is not None:
            lessons_by_day[l.weekday].append(l)

    header = {
        "plus": f"{header_prefix}\nНеделя ➕\n\n",
        "minus": f"{header_prefix}\nНеделя ➖\n\n",
        "full": f"{header_prefix}\nПолное расписание:\n\n"
    }.get(week, f"{header_prefix}\n\n")

    day_texts = []
    for wd in sorted(lessons_by_day.keys()):
        day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)
        day_block = f"🗓 *{escape_md_v2(weekday_names[wd])}*:\n" + "\n\n".join(format_lesson(l) for l in day_lessons) + "\n\n\n"
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