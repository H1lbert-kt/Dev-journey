from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import calendar as cal
from app.database.connection import get_db
from app.services.calendar_service import CalendarService
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def calendar_page(
    request: Request,
    year: int = Query(default=None),
    month: int = Query(default=None),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    calendar_service = CalendarService(db, user.id)
    today = date.today()

    if year is None:
        year = today.year
    if month is None:
        month = today.month

    days = calendar_service.get_days_by_month(year, month)
    days_dict = {d.date: d for d in days}

    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    first_weekday, num_days = cal.monthrange(year, month)

    calendar_days = []
    for _ in range(first_weekday):
        calendar_days.append(None)
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        day_data = days_dict.get(current_date)
        calendar_days.append({
            "day": day,
            "date": current_date,
            "studied": day_data.studied if day_data else False,
            "has_notes": bool(day_data.notes) if day_data else False,
            "notes": day_data.notes if day_data else "",
            "is_today": current_date == today,
        })

    return request.app.state.templates.TemplateResponse(
        request,
        "calendar.html",
        context={
            "year": year,
            "month": month,
            "calendar_days": calendar_days,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
        },
    )


@router.post("/mark-studied")
async def mark_studied(
    request: Request,
    study_date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    calendar_service = CalendarService(db, user.id)
    parsed_date = date.fromisoformat(study_date)
    calendar_service.mark_as_studied(parsed_date, notes if notes else None)
    url = f"/calendar?year={parsed_date.year}&month={parsed_date.month}"
    return RedirectResponse(url=url, status_code=303)


@router.post("/mark-not-studied")
async def mark_not_studied(
    request: Request,
    study_date: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    calendar_service = CalendarService(db, user.id)
    parsed_date = date.fromisoformat(study_date)
    calendar_service.mark_as_not_studied(parsed_date)
    url = f"/calendar?year={parsed_date.year}&month={parsed_date.month}"
    return RedirectResponse(url=url, status_code=303)


@router.post("/update-notes")
async def update_notes(
    request: Request,
    study_date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    calendar_service = CalendarService(db, user.id)
    parsed_date = date.fromisoformat(study_date)
    calendar_service.update_notes(parsed_date, notes)
    url = f"/calendar?year={parsed_date.year}&month={parsed_date.month}"
    return RedirectResponse(url=url, status_code=303)
