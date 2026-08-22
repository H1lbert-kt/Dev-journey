from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    daily_goal_minutes = Column(Integer, nullable=False, default=360)
    timer_state_seconds = Column(Integer, nullable=False, default=0)
    timer_state_subject = Column(String(100), nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now())

    phases = relationship("Phase", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    calendar_days = relationship("CalendarDay", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    study_sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="user", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="user", cascade="all, delete-orphan")
    simulados = relationship("Simulado", back_populates="user", cascade="all, delete-orphan")
    subject_goals = relationship("SubjectGoal", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    weekly_schedule = relationship("WeeklySchedule", back_populates="user", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="user", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    today_plan_items = relationship("TodayPlanItem", back_populates="user", cascade="all, delete-orphan")
