from sqlalchemy import Column, Integer, Date, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class CalendarDay(Base):
    __tablename__ = "calendar_days"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_calendar_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    studied = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="calendar_days")
