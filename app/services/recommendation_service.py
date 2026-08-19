from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from typing import Optional
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.simulado import Simulado
from app.models.flashcard import Flashcard
from app.models.today_plan import TodayPlanItem


class RecommendationService:
    """
    Deterministic recommendation engine.
    No AI — just data-driven logic.

    Weights for priority scoring:
    - recency:      30%  (days since last study)
    - performance:  25%  (simulado/flashcard scores)
    - balance:      20%  (weekly study balance)
    - pending:      15%  (pending plan items)
    - importance:   10%  (subject weight in goals/exams)
    """

    WEIGHTS = {
        "recency": 0.30,
        "performance": 0.25,
        "balance": 0.20,
        "pending": 0.15,
        "importance": 0.10,
    }

    def __init__(self, db: Session, user_id: int, study_mode: str = "programacao"):
        self.db = db
        self.user_id = user_id
        self.study_mode = study_mode
        self.today = date.today()
        self.week_start = self.today - timedelta(days=self.today.weekday())

    def get_next_action(self) -> Optional[dict]:
        """
        Returns the single best thing to do now.
        {
            "subject": "Física",
            "subject_id": 5,
            "subject_color": "#ff0000",
            "activity": "Estudar",
            "duration": 45,
            "reason": "Desempenho recente abaixo da média. Última sessão há 4 dias.",
            "priority_score": 8.7,
        }
        """
        subjects = self.db.query(Subject).filter(
            Subject.user_id == self.user_id,
            Subject.study_mode == self.study_mode,
        ).all()

        if not subjects:
            return None

        scored = []
        for subject in subjects:
            score_data = self._score_subject(subject)
            if score_data:
                scored.append(score_data)

        if not scored:
            return None

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        best = scored[0]

        return {
            "subject": best["subject"].name,
            "subject_id": best["subject"].id,
            "subject_color": best["subject"].color,
            "activity": self._suggest_activity(best),
            "duration": self._suggest_duration(best),
            "reason": self._build_reason(best),
            "priority_score": round(best["priority_score"], 1),
        }

    def get_weekly_report(self) -> dict:
        """
        Returns weekly summary for dashboard.
        """
        today = self.today
        week_start = self.week_start
        last_week_start = week_start - timedelta(days=7)
        last_week_end = week_start - timedelta(days=1)

        week_sessions = self.db.query(StudySession).filter(
            StudySession.user_id == self.user_id,
            StudySession.study_mode == self.study_mode,
            StudySession.date >= week_start,
        ).all()
        week_minutes = sum(s.duration_minutes for s in week_sessions)

        last_week_sessions = self.db.query(StudySession).filter(
            StudySession.user_id == self.user_id,
            StudySession.study_mode == self.study_mode,
            StudySession.date >= last_week_start,
            StudySession.date <= last_week_end,
        ).all()
        last_week_minutes = sum(s.duration_minutes for s in last_week_sessions)

        sessions_count = len(week_sessions)

        week_pct = 0
        if last_week_minutes > 0:
            week_pct = round((week_minutes - last_week_minutes) / last_week_minutes * 100)

        subject_minutes = {}
        for s in week_sessions:
            subject_minutes[s.subject] = subject_minutes.get(s.subject, 0) + s.duration_minutes

        best_subject = ""
        best_minutes = 0
        for name, mins in subject_minutes.items():
            if mins > best_minutes:
                best_subject = name
                best_minutes = mins

        attention_subjects = self._get_attention_subjects()

        return {
            "week_minutes": round(week_minutes, 1),
            "week_hours": round(week_minutes / 60, 1),
            "last_week_minutes": round(last_week_minutes, 1),
            "week_pct": week_pct,
            "sessions_count": sessions_count,
            "best_subject": best_subject,
            "attention_subjects": attention_subjects,
        }

    def _score_subject(self, subject: Subject) -> Optional[dict]:
        """Score a single subject for priority."""
        now = datetime.now()

        sessions = self.db.query(StudySession).filter(
            StudySession.user_id == self.user_id,
            StudySession.study_mode == self.study_mode,
            StudySession.subject == subject.name,
        ).order_by(StudySession.date.desc()).all()

        recency_score = self._recency_score(sessions)
        performance_score = self._performance_score(subject)
        balance_score = self._balance_score(subject.name)
        pending_score = self._pending_score(subject)
        importance_score = self._importance_score(subject)

        total = (
            recency_score * self.WEIGHTS["recency"]
            + performance_score * self.WEIGHTS["performance"]
            + balance_score * self.WEIGHTS["balance"]
            + pending_score * self.WEIGHTS["pending"]
            + importance_score * self.WEIGHTS["importance"]
        )

        return {
            "subject": subject,
            "total_score": total,
            "priority_score": total,
            "recency_score": recency_score,
            "performance_score": performance_score,
            "balance_score": balance_score,
            "pending_score": pending_score,
            "importance_score": importance_score,
            "last_session": sessions[0] if sessions else None,
            "week_minutes": sum(
                s.duration_minutes for s in sessions
                if s.date and s.date.date() >= self.week_start
            ),
        }

    def _recency_score(self, sessions) -> float:
        """0-100: higher = more urgent (longer since last study)."""
        if not sessions:
            return 100.0
        last = sessions[0]
        if not last.date:
            return 100.0
        days_since = (self.today - last.date.date()).days
        if days_since <= 1:
            return 0.0
        elif days_since <= 2:
            return 20.0
        elif days_since <= 3:
            return 40.0
        elif days_since <= 5:
            return 60.0
        elif days_since <= 7:
            return 80.0
        return 100.0

    def _performance_score(self, subject: Subject) -> float:
        """0-100: higher = worse performance (needs more attention)."""
        simulados = self.db.query(Simulado).filter(
            Simulado.user_id == self.user_id,
            Simulado.study_mode == self.study_mode,
        ).all()

        subject_simulados = []
        for s in simulados:
            if subject.name.lower() in (s.name or "").lower():
                subject_simulados.append(s)

        if not subject_simulados:
            flashcards = self.db.query(Flashcard).filter(
                Flashcard.user_id == self.user_id,
                Flashcard.subject_id == subject.id,
            ).all()
            if flashcards:
                avg_ease = sum(f.ease_factor for f in flashcards) / len(flashcards)
                if avg_ease < 1.5:
                    return 70.0
                elif avg_ease < 2.0:
                    return 40.0
                return 10.0
            return 50.0

        latest = subject_simulados[0]
        if latest.score is not None:
            if latest.score < 50:
                return 90.0
            elif latest.score < 70:
                return 60.0
            elif latest.score < 80:
                return 30.0
            return 5.0
        return 50.0

    def _balance_score(self, subject_name: str) -> float:
        """0-100: higher = disproportionately less studied this week."""
        week_sessions = self.db.query(StudySession).filter(
            StudySession.user_id == self.user_id,
            StudySession.study_mode == self.study_mode,
            StudySession.date >= self.week_start,
        ).all()

        if not week_sessions:
            return 50.0

        subject_minutes = {}
        for s in week_sessions:
            subject_minutes[s.subject] = subject_minutes.get(s.subject, 0) + s.duration_minutes

        if not subject_minutes:
            return 50.0

        avg_minutes = sum(subject_minutes.values()) / len(subject_minutes)
        subject_mins = subject_minutes.get(subject_name, 0)

        if avg_minutes == 0:
            return 50.0

        ratio = subject_mins / avg_minutes
        if ratio < 0.3:
            return 90.0
        elif ratio < 0.5:
            return 70.0
        elif ratio < 0.8:
            return 40.0
        elif ratio > 1.5:
            return 10.0
        return 20.0

    def _pending_score(self, subject: Subject) -> float:
        """0-100: higher = more pending plan items for this subject."""
        today = self.today
        pending = self.db.query(TodayPlanItem).filter(
            TodayPlanItem.user_id == self.user_id,
            TodayPlanItem.study_mode == self.study_mode,
            TodayPlanItem.subject_id == subject.id,
            TodayPlanItem.date == today,
            TodayPlanItem.completed == False,
        ).count()

        if pending >= 3:
            return 90.0
        elif pending >= 2:
            return 70.0
        elif pending >= 1:
            return 50.0
        return 10.0

    def _importance_score(self, subject: Subject) -> float:
        """0-100: higher = more important (linked to goals/exams)."""
        from app.models.study_goal import StudyGoal
        from app.models.exam import Exam
        from app.models.flashcard import Flashcard

        score = 0.0

        flashcard_count = self.db.query(Flashcard).filter(
            Flashcard.user_id == self.user_id,
            Flashcard.subject_id == subject.id,
        ).count()
        if flashcard_count > 10:
            score += 20.0
        elif flashcard_count > 5:
            score += 10.0

        active_goal = self.db.query(StudyGoal).filter(
            StudyGoal.user_id == self.user_id,
            StudyGoal.study_mode == self.study_mode,
            StudyGoal.active == True,
        ).first()
        if active_goal and active_goal.exam_id:
            score += 30.0

        return min(score, 100.0)

    def _suggest_activity(self, best: dict) -> str:
        if best["pending_score"] >= 50:
            return "Revisar"
        if best["performance_score"] >= 60:
            return "Praticar"
        if best["recency_score"] >= 80:
            return "Revisar"
        return "Estudar"

    def _suggest_duration(self, best: dict) -> int:
        if best["week_minutes"] == 0:
            return 45
        if best["week_minutes"] < 60:
            return 40
        if best["week_minutes"] < 180:
            return 30
        return 25

    def _build_reason(self, best: dict) -> str:
        reasons = []
        if best["performance_score"] >= 60:
            reasons.append("desempenho recente abaixo da média")
        if best["recency_score"] >= 60:
            days = 0
            if best["last_session"] and best["last_session"].date:
                days = (self.today - best["last_session"].date.date()).days
            if days > 0:
                reasons.append(f"última sessão há {days} dias")
        if best["balance_score"] >= 60:
            reasons.append("pouco tempo esta semana")
        if best["pending_score"] >= 50:
            reasons.append("tarefas pendentes no plano")
        if not reasons:
            reasons.append("manter o ritmo de estudos")
        return ". ".join(reasons[:2]) + "."

    def _get_attention_subjects(self) -> list:
        """Subjects that need attention (for weekly report)."""
        subjects = self.db.query(Subject).filter(
            Subject.user_id == self.user_id,
            Subject.study_mode == self.study_mode,
        ).all()

        attention = []
        for subject in subjects:
            sessions = self.db.query(StudySession).filter(
                StudySession.user_id == self.user_id,
                StudySession.study_mode == self.study_mode,
                StudySession.subject == subject.name,
            ).order_by(StudySession.date.desc()).all()

            if not sessions:
                attention.append({"name": subject.name, "color": subject.color, "reason": "nunca estudada"})
                continue

            days_since = (self.today - sessions[0].date.date()).days if sessions[0].date else 999
            if days_since >= 5:
                attention.append({"name": subject.name, "color": subject.color, "reason": f"há {days_since} dias"})

        return attention[:3]
