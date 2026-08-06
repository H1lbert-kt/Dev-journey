from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.models.habit import Habit
from app.repositories.habit_repository import HabitRepository


class HabitService:
    def __init__(self, db: Session, user_id: int):
        self.habit_repo = HabitRepository(db, user_id)
        self.user_id = user_id

    def get_habits_by_date(self, habit_date: date) -> List[Habit]:
        return self.habit_repo.get_by_date(habit_date)

    def get_habit_by_id(self, habit_id: int) -> Optional[Habit]:
        return self.habit_repo.get_by_id(habit_id)

    def create_habit(self, name: str, habit_date: date, icon: Optional[str] = None) -> Habit:
        habit = Habit(name=name, date=habit_date, icon=icon, user_id=self.user_id)
        return self.habit_repo.create(habit)

    def update_habit(self, habit_id: int, name: str, icon: Optional[str] = None) -> Optional[Habit]:
        habit = self.habit_repo.get_by_id(habit_id)
        if habit:
            return self.habit_repo.update(habit, {"name": name, "icon": icon})
        return None

    def toggle_habit(self, habit_id: int) -> Optional[Habit]:
        habit = self.habit_repo.get_by_id(habit_id)
        if habit:
            return self.habit_repo.update(habit, {"completed": not habit.completed})
        return None

    def delete_habit(self, habit_id: int) -> bool:
        return self.habit_repo.delete(habit_id)

    def all_completed(self, habit_date: date) -> bool:
        habits = self.habit_repo.get_by_date(habit_date)
        return len(habits) > 0 and all(h.completed for h in habits)
