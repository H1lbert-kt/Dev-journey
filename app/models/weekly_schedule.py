from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class WeeklySchedule(Base):
    __tablename__ = "weekly_schedule"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="weekly_schedule")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("user_id", "subject_id", "day_of_week", name="uq_user_subject_day"),
    )
