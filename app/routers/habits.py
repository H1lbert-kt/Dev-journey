from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.services.habit_service import HabitService
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def habits(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    habit_service = HabitService(db, user.id)
    today = date.today()
    habits = habit_service.get_habits_by_date(today)
    all_completed = habit_service.all_completed(today)

    return request.app.state.templates.TemplateResponse(
        request,
        "habits.html",
        context={
            "habits": habits,
            "today": today,
            "all_completed": all_completed,
            "study_mode": user.study_mode,
        },
    )


@router.post("/create")
async def create_habit(
    request: Request,
    name: str = Form(...),
    icon: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    habit_service = HabitService(db, user.id)
    today = date.today()
    habit_service.create_habit(name=name, habit_date=today, icon=icon if icon else None)
    return RedirectResponse(url="/habits", status_code=303)


@router.post("/{habit_id}/toggle")
async def toggle_habit(habit_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    habit_service = HabitService(db, user.id)
    habit_service.toggle_habit(habit_id)
    return RedirectResponse(url="/habits", status_code=303)


@router.post("/{habit_id}/update")
async def update_habit(
    habit_id: int,
    request: Request,
    name: str = Form(...),
    icon: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    habit_service = HabitService(db, user.id)
    habit_service.update_habit(habit_id, name=name, icon=icon if icon else None)
    return RedirectResponse(url="/habits", status_code=303)


@router.post("/{habit_id}/delete")
async def delete_habit(habit_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    habit_service = HabitService(db, user.id)
    habit_service.delete_habit(habit_id)
    return RedirectResponse(url="/habits", status_code=303)
