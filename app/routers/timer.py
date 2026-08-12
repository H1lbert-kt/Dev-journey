from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.database.connection import get_db
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.subject_goal import SubjectGoal
from app.models.calendar_day import CalendarDay
from app.models.weekly_schedule import WeeklySchedule
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def timer_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id
    ).order_by(StudySession.date.desc()).limit(20).all()

    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()

    today = datetime.now().date()
    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        func.date(StudySession.date) == today
    ).all()
    today_minutes = sum(s.duration_minutes for s in today_sessions)

    subject_goals = {}
    for goal in db.query(SubjectGoal).filter(SubjectGoal.user_id == user.id).all():
        subject_goals[goal.subject_id] = goal.daily_minutes

    subject_minutes = {}
    for s in today_sessions:
        subject_minutes[s.subject] = subject_minutes.get(s.subject, 0) + s.duration_minutes

    return request.app.state.templates.TemplateResponse(
        request,
        "timer.html",
        context={
            "sessions": sessions,
            "study_mode": user.study_mode,
            "subjects": subjects,
            "today_minutes": round(today_minutes, 1),
            "daily_goal": user.daily_goal_minutes,
            "subject_goals": subject_goals,
            "subject_minutes": subject_minutes,
        },
    )


@router.post("/save")
async def save_session(
    request: Request,
    subject: str = Form(...),
    duration: float = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not subject or not subject.strip():
        return JSONResponse(content={"error": "Materia obrigatoria"}, status_code=400)
    if duration < 0:
        return JSONResponse(content={"error": "Duracao invalida"}, status_code=400)

    session = StudySession(
        subject=subject.strip(),
        duration_minutes=round(duration / 60, 2),
        user_id=user.id,
    )
    db.add(session)

    today = date.today()
    day_of_week = today.weekday()

    schedule_entries = db.query(WeeklySchedule).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.day_of_week == day_of_week,
    ).all()

    day_completed = False

    if schedule_entries:
        scheduled_subject_ids = [e.subject_id for e in schedule_entries]
        scheduled_subject_names = []
        for sid in scheduled_subject_ids:
            subj = db.query(Subject).filter(Subject.id == sid).first()
            if subj:
                scheduled_subject_names.append(subj.name)

        studied_today = set()
        today_sessions = db.query(StudySession).filter(
            StudySession.user_id == user.id,
            func.date(StudySession.date) == today,
        ).all()
        for s in today_sessions:
            if s.subject in scheduled_subject_names:
                studied_today.add(s.subject)

        day_completed = len(scheduled_subject_names) > 0 and set(scheduled_subject_names) == studied_today
    else:
        day_completed = True

    calendar_day = db.query(CalendarDay).filter(
        CalendarDay.user_id == user.id,
        CalendarDay.date == today
    ).first()

    if calendar_day:
        calendar_day.studied = day_completed
    else:
        calendar_day = CalendarDay(
            date=today,
            studied=day_completed,
            user_id=user.id,
        )
        db.add(calendar_day)

    db.commit()

    return JSONResponse(content={"success": True, "day_completed": day_completed})


@router.post("/set-goal")
async def set_daily_goal(
    request: Request,
    daily_goal: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user.daily_goal_minutes = max(10, min(720, daily_goal))
    db.commit()
    return RedirectResponse(url="/timer", status_code=303)


@router.get("/check-day")
async def check_day_completed(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    today = date.today()
    day_of_week = today.weekday()

    schedule_entries = db.query(WeeklySchedule).filter(
        WeeklySchedule.user_id == user.id,
        WeeklySchedule.day_of_week == day_of_week,
    ).all()

    if not schedule_entries:
        return JSONResponse(content={"day_completed": False, "has_schedule": False})

    scheduled_subject_ids = [e.subject_id for e in schedule_entries]
    scheduled_subject_names = []
    for sid in scheduled_subject_ids:
        subj = db.query(Subject).filter(Subject.id == sid).first()
        if subj:
            scheduled_subject_names.append(subj.name)

    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        func.date(StudySession.date) == today,
    ).all()
    studied_today = {s.subject for s in today_sessions}

    day_completed = len(scheduled_subject_names) > 0 and set(scheduled_subject_names) == studied_today

    return JSONResponse(content={"day_completed": day_completed, "has_schedule": True})


@router.post("/set-subject-goal")
async def set_subject_goal(
    request: Request,
    subject_id: int = Form(...),
    daily_minutes: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if not subject:
        return RedirectResponse(url="/timer", status_code=303)

    existing = db.query(SubjectGoal).filter(
        SubjectGoal.subject_id == subject_id,
        SubjectGoal.user_id == user.id
    ).first()

    if existing:
        existing.daily_minutes = max(5, min(480, daily_minutes))
    else:
        goal = SubjectGoal(
            subject_id=subject_id,
            user_id=user.id,
            daily_minutes=max(5, min(480, daily_minutes)),
        )
        db.add(goal)

    db.commit()
    return RedirectResponse(url="/timer", status_code=303)


@router.get("/ping")
async def timer_ping():
    return JSONResponse(content={"status": "ok"})
