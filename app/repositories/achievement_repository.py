from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.achievement import Achievement


class AchievementRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_all(self) -> List[Achievement]:
        return self.db.query(Achievement).filter(Achievement.user_id == self.user_id).all()

    def get_by_id(self, achievement_id: int) -> Optional[Achievement]:
        return self.db.query(Achievement).filter(Achievement.id == achievement_id, Achievement.user_id == self.user_id).first()

    def get_unlocked(self) -> List[Achievement]:
        return self.db.query(Achievement).filter(Achievement.user_id == self.user_id, Achievement.unlocked == True).all()

    def create(self, achievement: Achievement) -> Achievement:
        self.db.add(achievement)
        self.db.commit()
        self.db.refresh(achievement)
        return achievement

    def update(self, achievement: Achievement, data: dict) -> Achievement:
        allowed_fields = {"name", "description", "icon", "unlocked", "unlocked_at"}
        for key, value in data.items():
            if value is not None and key in allowed_fields:
                setattr(achievement, key, value)
        self.db.commit()
        self.db.refresh(achievement)
        return achievement

    def delete(self, achievement_id: int) -> bool:
        achievement = self.get_by_id(achievement_id)
        if achievement:
            self.db.delete(achievement)
            self.db.commit()
            return True
        return False
