from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class StudyGoal(Base):
    __tablename__ = "study_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    goal_type = Column(String(20), nullable=False, default="concurso")
    title = Column(String(200), nullable=False)
    target_date = Column(Date, nullable=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)
    vestibular_name = Column(String(200), nullable=True)
    vestibular_institution = Column(String(200), nullable=True)
    vestibular_course = Column(String(200), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="study_goals")
    exam = relationship("Exam", foreign_keys=[exam_id])
