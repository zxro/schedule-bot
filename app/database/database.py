import asyncpg
from typing import List
from app.models.schedule import ScheduleItem


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)

    async def get_schedule_by_course(self, course: int) -> List[ScheduleItem]:
        """Получение расписания по номеру курса"""
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, course, day_of_week, time_start, time_end, subject, teacher, classroom
                FROM schedule 
                WHERE course = $1 
                ORDER BY 
                    CASE day_of_week
                        WHEN 'понедельник' THEN 1
                        WHEN 'вторник' THEN 2
                        WHEN 'среда' THEN 3
                        WHEN 'четверг' THEN 4
                        WHEN 'пятница' THEN 5
                        WHEN 'суббота' THEN 6
                        WHEN 'воскресенье' THEN 7
                    END,
                    time_start
                """,
                course
            )

            schedule = []
            for row in rows:
                schedule.append(ScheduleItem(
                    id=row['id'],
                    course=row['course'],
                    day_of_week=row['day_of_week'],
                    time_start=row['time_start'],
                    time_end=row['time_end'],
                    subject=row['subject'],
                    teacher=row['teacher'],
                    classroom=row['classroom']
                ))
            return schedule

    async def close(self):
        """Закрытие пула подключений"""
        if self.pool:
            await self.pool.close()