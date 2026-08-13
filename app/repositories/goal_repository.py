from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.goal import Goal
from app.models.phase import Phase


class GoalRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_all(self) -> List[Goal]:
        return self.db.query(Goal).join(Phase).filter(Phase.user_id == self.user_id).all()

    def get_by_id(self, goal_id: int) -> Optional[Goal]:
        return self.db.query(Goal).join(Phase).filter(Goal.id == goal_id, Phase.user_id == self.user_id).first()

    def get_by_phase(self, phase_id: int) -> List[Goal]:
        return self.db.query(Goal).join(Phase).filter(Goal.phase_id == phase_id, Phase.user_id == self.user_id).all()

    def create(self, goal: Goal) -> Goal:
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def update(self, goal: Goal, data: dict) -> Goal:
        allowed_fields = {"title", "completed"}
        for key, value in data.items():
            if value is not None and key in allowed_fields:
                setattr(goal, key, value)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def delete(self, goal_id: int) -> bool:
        goal = self.get_by_id(goal_id)
        if goal:
            self.db.delete(goal)
            self.db.commit()
            return True
        return False
