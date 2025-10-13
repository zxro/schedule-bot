import logging
import datetime

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.database.models import User, Lesson
import app.utils.week_mark as week_mark
from app.utils.schedule.schedule_formatter import format_schedule

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "Расписание на сегодня")
async def get_schedule_today(message: Message):
    """
    Отображает расписание на сегодняшний день для пользователя,
    исходя из его faculty_id и group_id в таблице user.
    """

    user_id = message.from_user.id
    today = datetime.date.today()
    weekday = today.isoweekday()  # Понедельник=1, ..., Воскресенье=7
    current_week_mark =  week_mark.WEEK_MARK_TXT
    print(f"current_week_mark = {current_week_mark}")

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("Вы ещё не зарегистрированы.")
                return

            group = user.group
            if not group:
                await message.answer("Ваша группа не найдена.")
                return

            result = await session.execute(
                select(Lesson)
                .where(Lesson.group_id == group.id)
                .where(Lesson.weekday == weekday)
            )
            lessons = result.scalars().all()

            lessons_today = [
                l for l in lessons
                if l.week_mark in ("every", current_week_mark)
            ]

            if not lessons_today:
                await message.answer("Сегодня пар нет 🎉")
                return

            text_blocks = format_schedule(
                lessons=lessons_today,
                week=current_week_mark,
                header_prefix=f"📅 Расписание на сегодня \\({today.strftime('%d\\.%m\\.%Y')}\\)"
            )

            for text in text_blocks:
                await message.answer(text, parse_mode="MarkdownV2")


    except Exception as e:
        logger.error(f"Ошибка при выводе расписания на сегодня: {e}")
        await message.answer("Ошибка при получении расписания.")