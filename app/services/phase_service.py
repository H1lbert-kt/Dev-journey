from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.phase import Phase
from app.repositories.phase_repository import PhaseRepository
from app.repositories.goal_repository import GoalRepository


class PhaseService:
    def __init__(self, db: Session, user_id: int, study_mode: Optional[str] = None):
        self.phase_repo = PhaseRepository(db, user_id, study_mode)
        self.goal_repo = GoalRepository(db, user_id, study_mode)
        self.user_id = user_id
        self.study_mode = study_mode

    def get_all_phases(self) -> List[Phase]:
        return self.phase_repo.get_all()

    def get_phase_by_id(self, phase_id: int) -> Optional[Phase]:
        return self.phase_repo.get_by_id(phase_id)

    def create_phase(self, name: str, description: Optional[str] = None, order: int = 0) -> Phase:
        phase = Phase(name=name, description=description, order=order, user_id=self.user_id, study_mode=self.study_mode or "programacao")
        return self.phase_repo.create(phase)

    def update_phase(self, phase_id: int, data: dict) -> Optional[Phase]:
        phase = self.phase_repo.get_by_id(phase_id)
        if phase:
            return self.phase_repo.update(phase, data)
        return None

    def delete_phase(self, phase_id: int) -> bool:
        return self.phase_repo.delete(phase_id)

    def calculate_progress(self, phase_id: int) -> float:
        goals = self.goal_repo.get_by_phase(phase_id)
        if not goals:
            return 0.0
        completed = sum(1 for g in goals if g.completed)
        return round((completed / len(goals)) * 100, 1)

    def update_phase_progress(self, phase_id: int) -> Optional[Phase]:
        phase = self.phase_repo.get_by_id(phase_id)
        if phase:
            progress = self.calculate_progress(phase_id)
            return self.phase_repo.update(phase, {"progress": progress})
        return None
