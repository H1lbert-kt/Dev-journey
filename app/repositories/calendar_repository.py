from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.models.calendar_day import CalendarDay


class CalendarRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_by_date(self, day_date: date) -> Optional[CalendarDay]:
        return self.db.query(CalendarDay).filter(CalendarDay.date == day_date, CalendarDay.user_id == self.user_id).first()

    def get_all(self) -> List[CalendarDay]:
        return self.db.query(CalendarDay).filter(CalendarDay.user_id == self.user_id).order_by(CalendarDay.date).all()

    def get_by_month(self, year: int, month: int) -> List[CalendarDay]:
        return (
            self.db.query(CalendarDay)
            .filter(
                CalendarDay.user_id == self.user_id,
                CalendarDay.date >= date(year, month, 1),
                CalendarDay.date < date(year + (month // 12), (month % 12) + 1, 1),
            )
            .order_by(CalendarDay.date)
            .all()
        )

    def create(self, calendar_day: CalendarDay) -> CalendarDay:
        self.db.add(calendar_day)
        self.db.commit()
        self.db.refresh(calendar_day)
        return calendar_day

    def update(self, calendar_day: CalendarDay, data: dict) -> CalendarDay:
        allowed_fields = {"studied", "notes"}
        for key, value in data.items():
            if value is not None and key in allowed_fields:
                setattr(calendar_day, key, value)
        self.db.commit()
        self.db.refresh(calendar_day)
        return calendar_day

    def delete(self, day_id: int) -> bool:
        calendar_day = self.db.query(CalendarDay).filter(CalendarDay.id == day_id, CalendarDay.user_id == self.user_id).first()
        if calendar_day:
            self.db.delete(calendar_day)
            self.db.commit()
            return True
        return False
