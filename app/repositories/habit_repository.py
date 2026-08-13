from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.models.habit import Habit


class HabitRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_by_date(self, habit_date: date) -> List[Habit]:
        return self.db.query(Habit).filter(Habit.date == habit_date, Habit.user_id == self.user_id).all()

    def get_by_id(self, habit_id: int) -> Optional[Habit]:
        return self.db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == self.user_id).first()

    def create(self, habit: Habit) -> Habit:
        self.db.add(habit)
        self.db.commit()
        self.db.refresh(habit)
        return habit

    def update(self, habit: Habit, data: dict) -> Habit:
        allowed_fields = {"name", "icon", "completed"}
        for key, value in data.items():
            if value is not None and key in allowed_fields:
                setattr(habit, key, value)
        self.db.commit()
        self.db.refresh(habit)
        return habit

    def delete(self, habit_id: int) -> bool:
        habit = self.get_by_id(habit_id)
        if habit:
            self.db.delete(habit)
            self.db.commit()
            return True
        return False
