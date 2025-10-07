"""
Определяет ORM-модели SQLAlchemy для хранения информации
о факультетах, группах, временных слотах и занятиях.

- Faculty: факультет
- Group: учебная группа
- TimeSlot: пара (начало/конец)
- Lesson: занятие с подробностями (преподаватели, аудитория, неделя и т.д.)
"""

from sqlalchemy import (
    Column, Integer, String, ForeignKey, Date, Time, Text, Enum, DateTime, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class WeekMarkEnum:
    """
    Псевдо-перечисление для SQLite, так как ENUM напрямую не поддерживается.
    """
    every = "every"
    plus = "plus"
    minus = "minus"

class Faculty(Base):
    """
    Модель факультета.

    Поля:
    id : int
        Первичный ключ.
    name : str
        Название факультета (уникальное).
    """

    __tablename__ = "faculties"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Group(Base):
    """
    Модель группы.

    Поля:
    id : int
        Первичный ключ.
    group_name : str
        Название группы (уникальное).
    faculty_id : int | None
        Внешний ключ на факультет.
    faculty : Faculty
        ORM-связь (joined-load).
    """

    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    group_name = Column(String, unique=True, nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="SET NULL"), nullable=True)
    faculty = relationship("Faculty", lazy="joined")

class TimeSlot(Base):
    """
    Модель временного интервала (пары).

    Поля:
    id : int
        Первичный ключ.
    lesson_number : int
        Номер пары.
    start_time : datetime.time
        Время начала.
    end_time : datetime.time
        Время конца.
    source_hash : str | None
        Хэш источника (опционально).
    """

    __tablename__ = "timeslots"
    id = Column(Integer, primary_key=True)
    lesson_number = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    source_hash = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('lesson_number', 'start_time', 'end_time', name='uq_timeslot'),
    )

class Lesson(Base):
    """
    Модель занятия (конкретное расписание).

    Поля:
    id : int
        Первичный ключ.
    group_id : int
        Внешний ключ на группу.
    date : datetime.date | None
        Дата занятия.
    weekday : int | None
        День недели (1–7).
    lesson_number : int | None
        Номер пары.
    start_time, end_time : datetime.time | None
        Время начала и конца.
    subject : str | None
        Предмет.
    professors : str | None
        Преподаватели.
    rooms : str | None
        Аудитории.
    week_mark : WeekMarkEnum | None
        Маркер недели (every/plus/minus).
    type : str | None
        Тип занятия (лекция, практика и т.д.)
    created_at : datetime
        Время создания записи.
    """

    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=True)
    weekday = Column(Integer, nullable=True)
    lesson_number = Column(Integer, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    subject = Column(Text, nullable=True)
    professors = Column(Text, nullable=True)
    rooms = Column(Text, nullable=True)
    week_mark = Column(String, nullable=True)  # заменено Enum -> String
    type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            'group_id', 'weekday', 'lesson_number', 'subject',
            'professors', 'rooms', 'week_mark', 'type',
            'start_time', 'end_time',
            name='uq_lesson_unique'
        ),
    )