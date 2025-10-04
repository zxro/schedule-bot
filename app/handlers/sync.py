from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import logging
from app.config import settings
from app.custom_logging.TelegramLogHandler import send_chat_info_log
from app.extracting_schedule.worker import run_full_sync_for_group, get_schedule_for_group
from app.keyboards.sync import get_sync_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text=="Запустить синхронизацию")
async def sync_chat(message: Message):
    """
    Обработчик команды кнопки "Запустить синхронизацию".

    Логика:
    1. Пользователь (админ) нажимает кнопку "Запустить синхронизацию".
    2. Бот отвечает сообщением "Выберите" и показывает клавиатуру
       для выбора конкретной группы или действия синхронизации.

    Аргументы:
    message : aiogram.types.Message
        Сообщение от пользователя (админа).
    """
    await message.answer(text="Выберите", reply_markup=get_sync_keyboard())

@router.message(F.text=="Синхронизация расписания для ПМиК-37")
async def sync_schedule(message: Message):
    """
    Асинхронный обработчик запуска полной синхронизации расписания группы ***.

    Логика:
    1. Отправляем сообщение пользователю и в лог-чат, что синхронизация началась.
    2. Создаем вложенную асинхронную функцию `background_sync`, которая:
       a. Вызывает `run_full_sync_for_group("ПМиК-37")` для полной синхронизации.
       b. Отправляет уведомление пользователю о завершении синхронизации.
       c. Логирует успешное завершение или ошибку через logger.
       d. В случае ошибки отправляет часть текста ошибки пользователю и логирует её.
    3. Запускаем `background_sync` через `asyncio.create_task` в фоне, чтобы не блокировать обработчик.

    Аргументы:
    message : aiogram.types.Message
        Сообщение от пользователя (админа).
    """

    chat_id = message.chat.id
    await message.answer("Синхронизация для ПМиК-37 началась ⏳")
    bot = message.bot
    await bot.send_message(settings.TELEGRAM_LOG_CHAT_ID, "Синхронизация для ПМиК-37 началась ⏳")

    async def background_sync():
        try:
            await run_full_sync_for_group("ПМиК-37")
            await message.bot.send_message(chat_id, "Синхронизация завершена ✅")
            logger.info("Синхронизация ПМиК-37 завершена")
            await send_chat_info_log(bot, "Синхронизация для ПМиК-37 завершена ⏳")
        except Exception as e:
            await send_chat_info_log(bot, f"Ошибка при синхронизации: {str(e)[:1000]}")
            logger.error(f"Ошибка при синхронизации ПМиК-37: {e}")

    asyncio.create_task(background_sync())

from collections import defaultdict
from aiogram.types import Message

@router.message(F.text == "Показать расписание ПМиК-37")
async def show_schedule(message: Message):
    """
    Обработчик вывода расписания группы *** пользователю.

    Логика:
    1. Получаем список пар через `get_schedule_for_group(***)`.
    2. Если пар нет, отправляем сообщение о пустом расписании.
    3. Группируем пары по дням недели (по полю `weekday`) с помощью defaultdict.
    4. Определяем словарь названий дней недели для удобного отображения.
    5. Форматируем каждую пару через вложенную функцию `format_lesson`:
       - Отображение времени начала/конца
       - Номер пары
       - Аудитория
       - Маркер недели (`plus`, `minus`, `every`)
    6. Формируем три текста для вывода:
       - "plus": пары плюс-недели
       - "minus": пары минус-недели
       - "all": полное расписание
    7. Для каждого дня недели сортируем уроки по `lesson_number` и добавляем в соответствующие тексты.
    8. Отправляем пользователю три сообщения с форматированным расписанием.
    9. В случае ошибки логируем её и уведомляем пользователя.

    Аргументы:
    message : aiogram.types.Message
        Сообщение от пользователя.
    """

    try:
        lessons = await get_schedule_for_group("ПМиК-37")
        if not lessons:
            await message.answer("Расписание для ПМиК-37 пустое.")
            return

        lessons_by_day = defaultdict(list)
        for l in lessons:
            if l.weekday is not None:
                lessons_by_day[l.weekday].append(l)

        week_order = sorted(lessons_by_day.keys())

        weekday_names = {
            1: "Понедельник",
            2: "Вторник",
            3: "Среда",
            4: "Четверг",
            5: "Пятница",
            6: "Суббота",
            7: "Воскресенье"
        }

        def format_lesson(l):
            start = l.start_time.strftime("%H:%M") if l.start_time else "??:??"
            end = l.end_time.strftime("%H:%M") if l.end_time else "??:??"
            lesson_num = l.lesson_number if l.lesson_number else "?"
            room = l.rooms if l.rooms else "Место проведения не указано"

            if l.week_mark == "plus":
                marker = "➕"
            elif l.week_mark == "minus":
                marker = "➖"
            else:  # every
                marker = "⚪"

            return f"  {marker} {lesson_num}: {l.subject} ({room}) ({start}-{end})"

        texts = {"plus": "📅 Плюсовая неделя:\n\n",
                 "minus": "📅 Минусовая неделя:\n\n",
                 "all": "📅 Всё расписание:\n\n"}

        for wd in week_order:
            day_lessons = sorted(lessons_by_day[wd], key=lambda x: x.lesson_number or 0)
            plus_lessons = [l for l in day_lessons if l.week_mark in ("every", "plus")]
            minus_lessons = [l for l in day_lessons if l.week_mark in ("every", "minus")]

            if plus_lessons:
                texts["plus"] += f"🗓 {weekday_names[wd]}:\n"
                texts["plus"] += "\n".join(format_lesson(l) for l in plus_lessons) + "\n\n"

            if minus_lessons:
                texts["minus"] += f"🗓 {weekday_names[wd]}:\n"
                texts["minus"] += "\n".join(format_lesson(l) for l in minus_lessons) + "\n\n"

            texts["all"] += f"🗓 {weekday_names[wd]}:\n"
            texts["all"] += "\n".join(format_lesson(l) for l in day_lessons) + "\n\n"

        await message.answer(texts["plus"])
        await message.answer(texts["minus"])
        await message.answer(texts["all"])

    except Exception as e:
        await message.answer(f"Ошибка при получении расписания: {str(e)[:1000]}")
        logger.error(f"Ошибка при выводе расписания ПМиК-37: {e}")

@router.message(Command("menu"))
async def show_keyboard(message: Message):
    """
    Обработчик команды /menu. Показывает пользователю клавиатуру с действиями.

    Логика:
    1. Получаем клавиатуру через функцию `get_sync_keyboard`.
    2. Отправляем пользователю сообщение "Выберите действие:" с клавиатурой.

    Аргументы:
    ----------
    message : aiogram.types.Message
        Сообщение от пользователя.
    """

    keyboard = get_sync_keyboard()
    await message.answer("Выберите действие:", reply_markup=keyboard)