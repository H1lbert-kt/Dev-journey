from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, func
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    ease_factor = Column(Float, nullable=False, default=2.5)
    interval_days = Column(Integer, nullable=False, default=0)
    next_review = Column(DateTime, nullable=False, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    review_count = Column(Integer, nullable=False, default=0)
    streak = Column(Integer, nullable=False, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    subject = relationship("Subject", back_populates="flashcards")
    user = relationship("User", back_populates="flashcards")
    reviews = relationship("FlashcardReview", back_populates="flashcard", cascade="all, delete-orphan")


class FlashcardReview(Base):
    __tablename__ = "flashcard_reviews"

    id = Column(Integer, primary_key=True, index=True)
    flashcard_id = Column(Integer, ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quality = Column(Integer, nullable=False)
    interval_before = Column(Integer, nullable=False)
    interval_after = Column(Integer, nullable=False)
    ease_factor_before = Column(Float, nullable=False)
    ease_factor_after = Column(Float, nullable=False)
    study_mode = Column(String(20), nullable=False, default="programacao")
    reviewed_at = Column(DateTime, default=datetime.now)

    flashcard = relationship("Flashcard", back_populates="reviews")
