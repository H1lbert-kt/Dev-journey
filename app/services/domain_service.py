from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Optional
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.flashcard import Flashcard
from app.models.simulado import Simulado


class DomainService:
    """
    Calculates estimated domain/health for a subject.

    Domain weights (adjustable):
    - simulados:   35%
    - flashcards:  25%
    - practice:    25%
    - recency:     15%
    """

    WEIGHTS = {
        "simulados": 0.35,
        "flashcards": 0.25,
        "practice": 0.25,
        "recency": 0.15,
    }

    def __init__(self, db: Session, user_id: int, study_mode: str = "programacao"):
        self.db = db
        self.user_id = user_id
        self.study_mode = study_mode
        self.today = date.today()

    def get_subject_domain(self, subject: Subject) -> dict:
        """
        Returns domain info for a subject:
        {
            "domain": 74,
            "health": "ok",  # ok, attention, critical
            "health_label": "Em dia",
            "days_since_last": 2,
            "detail": "Baseado no seu desempenho recente.",
        }
        """
        simulado_score = self._simulado_score(subject)
        flashcard_score = self._flashcard_score(subject)
        practice_score = self._practice_score(subject)
        recency_score = self._recency_score(subject)

        domain = round(
            simulado_score * self.WEIGHTS["simulados"]
            + flashcard_score * self.WEIGHTS["flashcards"]
            + practice_score * self.WEIGHTS["practice"]
            + recency_score * self.WEIGHTS["recency"]
        )
        domain = max(0, min(100, domain))

        days_since = self._days_since_last_study(subject)
        health, health_label = self._calculate_health(domain, days_since)

        return {
            "domain": domain,
            "health": health,
            "health_label": health_label,
            "days_since_last": days_since,
            "detail": self._build_detail(domain, days_since),
        }

    def get_all_subjects_domain(self) -> list:
        """Returns domain for all subjects."""
        subjects = self.db.query(Subject).filter(
            Subject.user_id == self.user_id,
            Subject.study_mode == self.study_mode,
        ).all()
        return [
            {"subject": s, **self.get_subject_domain(s)}
            for s in subjects
        ]

    def _simulado_score(self, subject: Subject) -> float:
        """0-100 based on simulado performance."""
        simulados = self.db.query(Simulado).filter(
            Simulado.user_id == self.user_id,
            Simulado.study_mode == self.study_mode,
        ).order_by(Simulado.created_at.desc()).limit(5).all()

        relevant = [s for s in simulados if subject.name.lower() in (s.name or "").lower()]

        if not relevant:
            return 50.0

        scores = [s.score for s in relevant if s.score is not None]
        if not scores:
            return 50.0

        return sum(scores) / len(scores)

    def _flashcard_score(self, subject: Subject) -> float:
        """0-100 based on flashcard SRS metrics."""
        flashcards = self.db.query(Flashcard).filter(
            Flashcard.user_id == self.user_id,
            Flashcard.subject_id == subject.id,
        ).all()

        if not flashcards:
            return 50.0

        total = len(flashcards)
        mature = sum(1 for f in flashcards if f.interval_days >= 21)
        young = sum(1 for f in flashcards if 1 <= f.interval_days < 21)
        avg_ease = sum(f.ease_factor for f in flashcards) / total

        if total == 0:
            return 50.0

        mature_pct = mature / total * 100
        ease_score = min(100, (avg_ease / 2.5) * 100)

        return (mature_pct * 0.6 + ease_score * 0.4)

    def _practice_score(self, subject: Subject) -> float:
        """0-100 based on recent study sessions."""
        sessions = self.db.query(StudySession).filter(
            StudySession.user_id == self.user_id,
            StudySession.study_mode == self.study_mode,
            StudySession.subject == subject.name,
        ).order_by(StudySession.date.desc()).limit(10).all()

        if not sessions:
            return 0.0

        total_minutes = sum(s.duration_minutes for s in sessions)
        session_count = len(sessions)

        if session_count >= 10 and total_minutes >= 300:
            return 90.0
        elif session_count >= 5 and total_minutes >= 150:
            return 70.0
        elif session_count >= 3 and total_minutes >= 60:
            return 50.0
        elif session_count >= 1:
            return 30.0
        return 0.0

    def _recency_score(self, subject: Subject) -> float:
        """0-100: higher = more recent (better)."""
        days = self._days_since_last_study(subject)
        if days is None:
            return 0.0
        if days <= 1:
            return 100.0
        elif days <= 3:
            return 70.0
        elif days <= 5:
            return 40.0
        elif days <= 7:
            return 20.0
        return 5.0

    def _days_since_last_study(self, subject: Subject) -> Optional[int]:
        last = self.db.query(StudySession).filter(
            StudySession.user_id == self.user_id,
            StudySession.study_mode == self.study_mode,
            StudySession.subject == subject.name,
        ).order_by(StudySession.date.desc()).first()

        if not last or not last.date:
            return None
        return (self.today - last.date.date()).days

    def _calculate_health(self, domain: int, days_since: Optional[int]) -> tuple:
        """Returns (health, health_label)."""
        if domain < 30 or (days_since is not None and days_since >= 7):
            return "critical", "Precisa de atenção"
        elif domain < 60 or (days_since is not None and days_since >= 4):
            return "attention", "Atenção"
        return "ok", "Em dia"

    def _build_detail(self, domain: int, days_since: Optional[int]) -> str:
        parts = []
        if domain >= 70:
            parts.append("bom desempenho")
        elif domain >= 40:
            parts.append("desempenho moderado")
        else:
            parts.append("desempenho baixo")

        if days_since is not None:
            if days_since == 0:
                parts.append("estudado hoje")
            elif days_since == 1:
                parts.append("estudado ontem")
            else:
                parts.append(f"há {days_since} dias")

        return "Baseado no seu desempenho recente."
