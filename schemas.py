from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import date, datetime

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: int = 0
    tags: Optional[List[str]] = None
    due_date: Optional[date] = None
    recurrence_pattern: Optional[str] = None
    recurrence_start_date: Optional[date] = None
    recurrence_end_date: Optional[date] = None
    reminder_time: Optional[datetime] = None

    @validator('recurrence_pattern')
    def validate_recurrence_pattern(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Recurrence pattern cannot be an empty string')
        # Here you could add more complex validation, e.g., regex for iCalendar RRULE
        return v

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    due_date: Optional[date] = None
    recurrence_pattern: Optional[str] = None
    recurrence_start_date: Optional[date] = None
    recurrence_end_date: Optional[date] = None
    reminder_time: Optional[datetime] = None

class Task(TaskBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
