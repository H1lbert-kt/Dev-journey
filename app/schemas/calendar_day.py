from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class CalendarDayCreate(BaseModel):
    date: date
    studied: bool = False
    notes: Optional[str] = None


class CalendarDayUpdate(BaseModel):
    studied: Optional[bool] = None
    notes: Optional[str] = None


class CalendarDayResponse(BaseModel):
    id: int
    date: date
    studied: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
