from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class HabitCreate(BaseModel):
    name: str
    icon: Optional[str] = None
    date: date
    completed: bool = False


class HabitResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str]
    date: date
    completed: bool
    created_at: datetime

    class Config:
        from_attributes = True
