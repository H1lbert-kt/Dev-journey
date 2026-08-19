from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, func
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import date


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="journal_entries")
    project = relationship("Project", back_populates="journal_entries")
    subject = relationship("Subject", back_populates="journal_entries")
