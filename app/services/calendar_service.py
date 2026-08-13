from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.models.calendar_day import CalendarDay
from app.repositories.calendar_repository import CalendarRepository


class CalendarService:
    def __init__(self, db: Session, user_id: int):
        self.calendar_repo = CalendarRepository(db, user_id)
        self.user_id = user_id

    def get_day_by_date(self, day_date: date) -> Optional[CalendarDay]:
        return self.calendar_repo.get_by_date(day_date)

    def get_all_days(self) -> List[CalendarDay]:
        return self.calendar_repo.get_all()

    def get_days_by_month(self, year: int, month: int) -> List[CalendarDay]:
        return self.calendar_repo.get_by_month(year, month)

    def mark_as_studied(self, day_date: date, notes: Optional[str] = None) -> CalendarDay:
        existing = self.calendar_repo.get_by_date(day_date)
        if existing:
            return self.calendar_repo.update(existing, {"studied": True, "notes": notes})
        calendar_day = CalendarDay(date=day_date, studied=True, notes=notes, user_id=self.user_id)
        return self.calendar_repo.create(calendar_day)

    def mark_as_not_studied(self, day_date: date) -> CalendarDay:
        existing = self.calendar_repo.get_by_date(day_date)
        if existing:
            return self.calendar_repo.update(existing, {"studied": False})
        calendar_day = CalendarDay(date=day_date, studied=False, user_id=self.user_id)
        return self.calendar_repo.create(calendar_day)

    def update_notes(self, day_date: date, notes: str) -> Optional[CalendarDay]:
        existing = self.calendar_repo.get_by_date(day_date)
        if existing:
            return self.calendar_repo.update(existing, {"notes": notes})
        calendar_day = CalendarDay(date=day_date, studied=False, notes=notes, user_id=self.user_id)
        return self.calendar_repo.create(calendar_day)

    def get_total_studied_days(self) -> int:
        days = self.calendar_repo.get_all()
        return sum(1 for d in days if d.studied)

    def get_current_streak(self) -> int:
        days = self.calendar_repo.get_all()
        studied_days = sorted([d.date for d in days if d.studied], reverse=True)
        if not studied_days:
            return 0

        today = date.today()
        streak = 0
        current_date = today

        if studied_days[0] < current_date:
            current_date = date.fromordinal(current_date.toordinal() - 1)

        for studied_date in studied_days:
            if studied_date == current_date:
                streak += 1
                current_date = date.fromordinal(current_date.toordinal() - 1)
            elif studied_date < current_date:
                break

        return streak
