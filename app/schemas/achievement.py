from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AchievementCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class AchievementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    unlocked: Optional[bool] = None


class AchievementResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    unlocked: bool
    unlocked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
