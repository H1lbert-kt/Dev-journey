from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.phase import Phase


class PhaseRepository:
    def __init__(self, db: Session, user_id: int, study_mode: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.study_mode = study_mode

    def _base_query(self):
        q = self.db.query(Phase).filter(Phase.user_id == self.user_id)
        if self.study_mode is not None:
            q = q.filter(Phase.study_mode == self.study_mode)
        return q

    def get_all(self) -> List[Phase]:
        return self._base_query().order_by(Phase.order).all()

    def get_by_id(self, phase_id: int) -> Optional[Phase]:
        return self._base_query().filter(Phase.id == phase_id).first()

    def create(self, phase: Phase) -> Phase:
        self.db.add(phase)
        self.db.commit()
        self.db.refresh(phase)
        return phase

    def update(self, phase: Phase, data: dict) -> Phase:
        allowed_fields = {"name", "description", "order", "progress"}
        for key, value in data.items():
            if value is not None and key in allowed_fields:
                setattr(phase, key, value)
        self.db.commit()
        self.db.refresh(phase)
        return phase

    def delete(self, phase_id: int) -> bool:
        phase = self.get_by_id(phase_id)
        if phase:
            self.db.delete(phase)
            self.db.commit()
            return True
        return False
