from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.achievement import Achievement
from app.repositories.achievement_repository import AchievementRepository


class AchievementService:
    def __init__(self, db: Session, user_id: int):
        self.achievement_repo = AchievementRepository(db, user_id)
        self.user_id = user_id

    def get_all_achievements(self) -> List[Achievement]:
        return self.achievement_repo.get_all()

    def get_achievement_by_id(self, achievement_id: int) -> Optional[Achievement]:
        return self.achievement_repo.get_by_id(achievement_id)

    def get_unlocked_achievements(self) -> List[Achievement]:
        return self.achievement_repo.get_unlocked()

    def create_achievement(self, name: str, description: Optional[str] = None, icon: Optional[str] = None) -> Achievement:
        achievement = Achievement(name=name, description=description, icon=icon, user_id=self.user_id)
        return self.achievement_repo.create(achievement)

    def unlock_achievement(self, achievement_id: int) -> Optional[Achievement]:
        achievement = self.achievement_repo.get_by_id(achievement_id)
        if achievement and not achievement.unlocked:
            return self.achievement_repo.update(achievement, {
                "unlocked": True,
                "unlocked_at": datetime.now()
            })
        return achievement

    def update_achievement(self, achievement_id: int, data: dict) -> Optional[Achievement]:
        achievement = self.achievement_repo.get_by_id(achievement_id)
        if achievement:
            return self.achievement_repo.update(achievement, data)
        return None

    def delete_achievement(self, achievement_id: int) -> bool:
        return self.achievement_repo.delete(achievement_id)

    def get_unlocked_count(self) -> int:
        return len(self.achievement_repo.get_unlocked())

    def initialize_default_achievements(self) -> List[Achievement]:
        return self.achievement_repo.get_all()
