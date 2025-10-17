"""
Определяет ORM-модели SQLAlchemy для хранения информации
о факультетах, группах, временных слотах и занятиях.

- Faculty: факультет
- Group: учебная группа
- TimeSlot: пара (начало/конец)
- Lesson: занятие
- Users: пользователь
"""

from sqlalchemy import (
    Column, Integer, String, ForeignKey, Time, Text, UniqueConstraint
)
from sqlalchemy.dialects.mysql import SMALLINT
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

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
    weekday = Column(Integer, nullable=True)
    lesson_number = Column(Integer, nullable=True)
    subject = Column(Text, nullable=True)
    professors = Column(Text, nullable=True)
    rooms = Column(Text, nullable=True)
    week_mark = Column(String, nullable=True)
    type = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'group_id', 'weekday', 'lesson_number', 'subject',
            'professors', 'rooms', 'week_mark', 'type',
            name='uq_lesson_unique'
        ),
    )

class User(Base):
    """
    Пользователь

    Поля:
    id : SMALL INTEGER
        Первичный ключ(берется id пользователя его телеграм аккаунта)
    group_id : Integer
        Внешний ключ на группу.
   faculty_id : Integer
        Внешний ключ на факультет.
    """
    __tablename__ = "users"

    id = Column(SMALLINT, primary_key=True)  # Telegram user_id
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False, index=True)

    group = relationship("Group", lazy="joined")
    faculty = relationship("Faculty", lazy="joined")

    __table_args__ = (
        UniqueConstraint('id', name='uq_user_id'),
    )