from sqlalchemy import (
    Column, Integer, String, ForeignKey, Date, Time, Text, Enum, DateTime, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class WeekMarkEnum(str, enum.Enum):
    every = "every"
    plus = "plus"
    minus = "minus"

class Faculty(Base):
    __tablename__ = "faculties"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    group_name = Column(String, unique=True, nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey(column="faculties.id", ondelete="SET NULL"), nullable=True)

    faculty = relationship(argument="Faculty", lazy="joined")

class TimeSlot(Base):
    __tablename__ = "timeslots"
    id = Column(Integer, primary_key=True)
    lesson_number = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    source_hash = Column(String, nullable=True)  # optional fingerprint
    __table_args__ = (UniqueConstraint('lesson_number', 'start_time', 'end_time', name='uq_timeslot'),)

class Lesson(Base):
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
    week_mark = Column(Enum(WeekMarkEnum), nullable=True)
    type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    raw_json = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint('group_id', 'date', 'lesson_number', 'week_mark', 'type', name='uq_lesson_unique'),
    )