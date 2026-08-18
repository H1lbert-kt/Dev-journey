from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class Simulado(Base):
    __tablename__ = "simulados"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    total_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    wrong_answers = Column(Integer, nullable=False, default=0)
    null_answers = Column(Integer, nullable=False, default=0)
    correction_method = Column(String(20), nullable=False, default="normal")
    final_score = Column(Float, nullable=True)
    time_minutes = Column(Float, nullable=False, default=0.0)
    score = Column(Float, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="simulados")
