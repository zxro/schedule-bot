"""
Модуль автоматической синхронизации расписания.

Назначение:
    Модуль управляет планированием регулярных запусков функции синхронизации расписания.
    - В сентябре и октябре синхронизация выполняется каждый день ночью.
    - В остальные месяцы — один раз в месяц (в последний день месяца).

Основные функции:
    1. schedule_sync_task() — запускает фоновую задачу планировщика.
    2. _should_run_today() — проверяет, нужно ли выполнять синхронизацию сегодня.
    3. _scheduler_loop() — бесконечный цикл, который ждёт подходящего времени и вызывает run_full_sync().

Используемые компоненты:
    - run_full_sync() из app.utils.schedule.sync_functions (или вашего модуля синхронизации)
    - asyncio для фонового выполнения
    - logging для детального логирования всех этапов
"""

import asyncio
import logging
from datetime import datetime, timedelta

from app.utils.schedule.worker import run_full_sync

logger = logging.getLogger(__name__)


async def _should_run_today() -> bool:
    """
    Проверяет, должна ли выполняться синхронизация сегодня.

    Логика:
    1. Для сентября и октября — всегда возвращает True (ежедневная синхронизация).
    2. Для остальных месяцев — True только если сегодня последний день месяца.

    Возвращает:
        bool: True, если сегодня нужно запустить синхронизацию.
    """

    today = datetime.now()
    month = today.month

    # Сентябрь и октябрь — ежедневная синхронизация
    if month in (9, 10):
        return True

    # Для остальных месяцев — только в последний день месяца
    tomorrow = today + timedelta(days=1)
    return tomorrow.month != month


async def _scheduler_loop():
    """
    Основной цикл планировщика, который:
    1. Проверяет, нужно ли запустить синхронизацию сегодня.
    2. Если нужно — вызывает run_full_sync().
    3. Ждёт до следующего дня (в 03:00 ночи).
    """

    while True:
        now = datetime.now()
        target_time = datetime(now.year, now.month, now.day, 3, 0, 0)  # 03:00 ночи

        # Если текущее время уже после 03:00 — планируем на следующую ночь
        if now >= target_time:
            target_time += timedelta(days=1)

        sleep_seconds = (target_time - now).total_seconds()
        logger.info(f"🕒 Следующая автоматическая синхронизация запланирована на {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        await asyncio.sleep(sleep_seconds)

        # Проверяем, нужно ли выполнять синхронизацию
        if await _should_run_today():
            try:
                logger.info("🚀 Запуск автоматической синхронизации расписания...")
                await run_full_sync()
                logger.info("✅ Автоматическая синхронизация успешно завершена.")
            except Exception as e:
                logger.error(f"❌ Ошибка при автоматической синхронизации: {e}")


async def schedule_sync_task():
    """
    Запускает фоновую задачу планировщика синхронизации расписания.
    """

    logger.info("🗓️ Планировщик синхронизации расписания запущен.")
    await _scheduler_loop()
