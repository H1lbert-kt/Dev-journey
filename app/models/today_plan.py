from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Boolean, func
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import date


class TodayPlanItem(Base):
    __tablename__ = "today_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    time_optional = Column(String(5), nullable=True)
    priority = Column(String(10), nullable=False, default="media")
    completed = Column(Boolean, nullable=False, default=False)
    item_type = Column(String(20), nullable=False, default="estudo")
    date = Column(Date, nullable=False, default=date.today)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="today_plan_items")
    subject = relationship("Subject", back_populates="today_plan_items")
