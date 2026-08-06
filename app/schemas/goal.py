from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GoalCreate(BaseModel):
    title: str
    phase_id: int


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None


class GoalResponse(BaseModel):
    id: int
    title: str
    completed: bool
    phase_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
