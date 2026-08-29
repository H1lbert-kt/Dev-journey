from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.subject import Subject
from app.models.weekly_schedule import WeeklySchedule
from app.models.study_session import StudySession
from app.routers.auth import require_auth
from datetime import datetime, date

router = APIRouter()

DAYS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]


@router.get("/")
async def schedule_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subjects = db.query(Subject).filter(Subject.user_id == user.id, Subject.study_mode == user.study_mode).all()

    schedule = {}
    for day_idx in range(7):
        schedule[day_idx] = []

    for entry in db.query(WeeklySchedule).join(Subject, WeeklySchedule.subject_id == Subject.id).filter(
        WeeklySchedule.user_id == user.id,
        Subject.study_mode == user.study_mode,
    ).order_by(WeeklySchedule.day_of_week, WeeklySchedule.order).all():
        if entry.subject:
            schedule[entry.day_of_week].append({
                "id": entry.id,
                "subject_id": entry.subject_id,
                "name": entry.subject.name,
                "color": entry.subject.color,
                "order": entry.order,
            })

    today_minutes = {}
    today = datetime.now().date()
    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        func.date(StudySession.date) == today,
    ).all()
    studied_names_today = {s.subject for s in today_sessions}
    for s in today_sessions:
        today_minutes[s.subject] = today_minutes.get(s.subject, 0) + s.duration_minutes

    completed_days = {}
    today_idx = today.weekday()

    for day_idx in range(7):
        if day_idx != today_idx:
            completed_days[day_idx] = False
            continue
        day_subjects = schedule[day_idx]
        if not day_subjects:
            completed_days[day_idx] = False
            continue
        all_studied = all(item["name"] in studied_names_today for item in day_subjects)
        completed_days[day_idx] = all_studied

    return request.app.state.templates.TemplateResponse(
        request,
        "schedule.html",
        context={
            "subjects": subjects,
            "schedule": schedule,
            "days": DAYS,
            "today_minutes": today_minutes,
            "study_mode": user.study_mode,
            "completed_days": completed_days,
        },
    )


@router.post("/add")
async def add_to_schedule(
    request: Request,
    subject_id: int = Form(...),
    day_of_week: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id, Subject.study_mode == user.study_mode).first()
    if not subject:
        return RedirectResponse(url="/schedule", status_code=303)

    if not (0 <= day_of_week <= 6):
        return RedirectResponse(url="/schedule", status_code=303)

    existing = db.query(WeeklySchedule).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.subject_id == subject_id,
        WeeklySchedule.day_of_week == day_of_week,
    ).first()

    if existing:
        return RedirectResponse(url="/schedule", status_code=303)

    max_order = db.query(WeeklySchedule).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.day_of_week == day_of_week,
    ).count()

    entry = WeeklySchedule(
        user_id=user.id,
        subject_id=subject_id,
        day_of_week=day_of_week,
        order=max_order,
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/schedule", status_code=303)


@router.post("/remove")
async def remove_from_schedule(
    request: Request,
    schedule_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    entry = db.query(WeeklySchedule).filter(
        WeeklySchedule.id == schedule_id,
        WeeklySchedule.user_id == user.id,
    ).first()
    if entry:
        db.delete(entry)
        try:
            db.commit()
        except Exception:
            db.rollback()
    return RedirectResponse(url="/schedule", status_code=303)


@router.post("/reorder")
async def reorder_schedule(
    request: Request,
    schedule_id: int = Form(...),
    new_order: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    entry = db.query(WeeklySchedule).filter(
        WeeklySchedule.id == schedule_id,
        WeeklySchedule.user_id == user.id,
    ).first()
    if not entry:
        return RedirectResponse(url="/schedule", status_code=303)

    day = entry.day_of_week
    items = db.query(WeeklySchedule).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.day_of_week == day,
    ).order_by(WeeklySchedule.order).all()

    items = [i for i in items if i.id != schedule_id]
    new_order = max(0, min(new_order, len(items)))
    items.insert(new_order, entry)

    for idx, item in enumerate(items):
        item.order = idx

    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/schedule", status_code=303)


@router.get("/api/{day_of_week}")
async def get_day_schedule(day_of_week: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    if not (0 <= day_of_week <= 6):
        return JSONResponse(content={"error": "day_of_week must be 0-6"}, status_code=400)

    entries = db.query(WeeklySchedule).join(Subject, WeeklySchedule.subject_id == Subject.id).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.day_of_week == day_of_week,
        Subject.study_mode == user.study_mode,
    ).order_by(WeeklySchedule.order).all()

    subjects = []
    for entry in entries:
        if entry.subject:
            subjects.append({
                "id": entry.subject_id,
                "name": entry.subject.name,
                "color": entry.subject.color,
            })

    return JSONResponse(content={"subjects": subjects})
