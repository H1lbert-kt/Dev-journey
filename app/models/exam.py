from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=True)
    position = Column(String(200), nullable=True)
    banca = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="planejando")
    exam_date = Column(Date, nullable=True)
    salary = Column(String(50), nullable=True)
    vacancies = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

    user = relationship("User", back_populates="exams")
    subjects = relationship("ExamSubject", back_populates="exam", cascade="all, delete-orphan")


class ExamSubject(Base):
    __tablename__ = "exam_subjects"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    progress = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

    exam = relationship("Exam", back_populates="subjects")
