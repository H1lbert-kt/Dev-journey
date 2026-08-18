from sqlalchemy.orm import Session
from datetime import date
from app.services.phase_service import PhaseService
from app.services.goal_service import GoalService
from app.services.project_service import ProjectService
from app.services.calendar_service import CalendarService


class DashboardService:
    def __init__(self, db: Session, user_id: int, study_mode: str = "programacao"):
        self.phase_service = PhaseService(db, user_id, study_mode)
        self.goal_service = GoalService(db, user_id, study_mode)
        self.project_service = ProjectService(db, user_id, study_mode)
        self.calendar_service = CalendarService(db, user_id)

    def get_dashboard_data(self) -> dict:
        phases = self.phase_service.get_all_phases()
        all_goals = self.goal_service.get_all_goals()
        completed_goals = [g for g in all_goals if g.completed]
        completed_projects = self.project_service.get_completed_count()
        studied_days = self.calendar_service.get_total_studied_days()
        total_progress = 0.0

        if phases:
            total_progress = round(sum(p.progress for p in phases) / len(phases), 1)

        return {
            "total_progress": total_progress,
            "completed_goals": len(completed_goals),
            "pending_goals": len(all_goals) - len(completed_goals),
            "completed_phases": sum(1 for p in phases if p.progress >= 99.9),
            "completed_projects": completed_projects,
            "studied_days": studied_days,
        }
