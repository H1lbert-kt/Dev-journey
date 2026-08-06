from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.goal import Goal
from app.repositories.goal_repository import GoalRepository
from app.services.phase_service import PhaseService


class GoalService:
    def __init__(self, db: Session, user_id: int):
        self.goal_repo = GoalRepository(db, user_id)
        self.phase_service = PhaseService(db, user_id)
        self.user_id = user_id

    def get_all_goals(self) -> List[Goal]:
        return self.goal_repo.get_all()

    def get_goal_by_id(self, goal_id: int) -> Optional[Goal]:
        return self.goal_repo.get_by_id(goal_id)

    def get_goals_by_phase(self, phase_id: int) -> List[Goal]:
        return self.goal_repo.get_by_phase(phase_id)

    def create_goal(self, title: str, phase_id: int) -> Goal:
        goal = Goal(title=title, phase_id=phase_id)
        created = self.goal_repo.create(goal)
        self.phase_service.update_phase_progress(phase_id)
        return created

    def update_goal(self, goal_id: int, data: dict) -> Optional[Goal]:
        goal = self.goal_repo.get_by_id(goal_id)
        if goal:
            updated = self.goal_repo.update(goal, data)
            self.phase_service.update_phase_progress(goal.phase_id)
            return updated
        return None

    def toggle_goal(self, goal_id: int) -> Optional[Goal]:
        goal = self.goal_repo.get_by_id(goal_id)
        if goal:
            updated = self.goal_repo.update(goal, {"completed": not goal.completed})
            self.phase_service.update_phase_progress(goal.phase_id)
            return updated
        return None

    def delete_goal(self, goal_id: int) -> bool:
        goal = self.goal_repo.get_by_id(goal_id)
        if goal:
            phase_id = goal.phase_id
            deleted = self.goal_repo.delete(goal_id)
            if deleted:
                self.phase_service.update_phase_progress(phase_id)
            return deleted
        return False
