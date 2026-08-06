from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PhaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0


class PhaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class PhaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    order: int
    progress: float
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
