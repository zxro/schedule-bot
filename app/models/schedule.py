from pydantic import BaseModel
from typing import Optional
from datetime import time

class ScheduleItem(BaseModel):
    id: int
    course: int
    day_of_week: str
    time_start: time
    time_end: time
    subject: str
    teacher: str
    classroom: Optional[str] = None