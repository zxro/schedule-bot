"""
Определяет ORM-модели SQLAlchemy для хранения информации
о факультетах, группах, временных слотах и занятиях.

- Faculty: факультет
- Group: учебная группа
- Lesson: занятие
- Users: пользователь
"""

from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, UniqueConstraint
)

from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Faculty(Base):
    """
    Модель факультета.

    Поля:
    id : Integer
        Первичный ключ.
    name : String
        Название факультета (уникальное).
    """

    __tablename__ = "faculties"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Group(Base):
    """
    Модель группы.

    Поля:
    id : Integer
        Первичный ключ.
    group_name : str
        Название группы (уникальное).
    faculty_id : Integer | None
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
    id : Integer
        Первичный ключ.
    group_id : Integer
        Внешний ключ на группу.
    weekday : Integer | None
        День недели (1–7).
    lesson_number : int | None
        Номер пары.
    subject : String | None
        Предмет.
    professors : String | None
        Преподаватели.
    rooms : String | None
        Аудитории.
    week_mark : WeekMarkEnum | None
        Маркер недели (every/plus/minus).
    type : String | None
        Тип занятия (лекция, практика и т.д.)
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
    id : Integer
        Первичный ключ (берется id пользователя его телеграм аккаунта)
    group_id : Integer
        Внешний ключ на группу.
   faculty_id : Integer
        Внешний ключ на факультет.
    role : Integer
        Роль пользователя (0-9), по умолчанию 0.
        0 - пользователь
        1 - админ
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # Telegram user_id
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Integer, nullable=False, default=0)

    group = relationship("Group", lazy="joined")
    faculty = relationship("Faculty", lazy="joined")

    __table_args__ = (
        UniqueConstraint('id', name='uq_user_id'),
    )