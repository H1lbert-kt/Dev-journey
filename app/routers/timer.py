from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional
from app.database.connection import get_db
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.calendar_day import CalendarDay
from app.models.weekly_schedule import WeeklySchedule
from app.models.exam import Exam
from app.models.project import Project
from app.models.today_plan import TodayPlanItem
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def timer_page(
    request: Request,
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None),
    duration: Optional[int] = Query(None),
    auto_start: Optional[int] = Query(None),
    plan_item: Optional[int] = Query(None),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode
    ).order_by(StudySession.date.desc()).limit(10).all()

    subjects = db.query(Subject).filter(Subject.user_id == user.id, Subject.study_mode == user.study_mode).all()

    exams = db.query(Exam).filter(Exam.user_id == user.id, Exam.study_mode == user.study_mode).all()
    projects = db.query(Project).filter(Project.user_id == user.id, Project.study_mode == user.study_mode).all()

    today = datetime.now().date()
    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        func.date(StudySession.date) == today
    ).all()
    today_minutes = sum(s.duration_minutes for s in today_sessions)

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
            "exams": exams,
            "projects": projects,
            "today_minutes": round(today_minutes, 1),
            "daily_goal": user.daily_goal_minutes,
            "subject_minutes": subject_minutes,
            "auto_subject": subject,
            "auto_duration": duration,
            "auto_start": auto_start == 1 if auto_start else False,
            "plan_item_id": plan_item,
        },
    )


@router.post("/save")
async def save_session(
    request: Request,
    subject: str = Form(...),
    duration: float = Form(...),
    session_type: str = Form("estudo"),
    exam_id: int = Form(None),
    project_id: int = Form(None),
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not subject or not subject.strip():
        return JSONResponse(content={"error": "Materia obrigatoria"}, status_code=400)
    if duration < 0:
        return JSONResponse(content={"error": "Duracao invalida"}, status_code=400)
    if session_type not in ("estudo", "teoria", "exercicios", "revisao", "projeto", "simulado"):
        session_type = "estudo"

    validated_exam_id = None
    if exam_id:
        if db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first():
            validated_exam_id = exam_id

    validated_project_id = None
    if project_id:
        if db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first():
            validated_project_id = project_id

    existing_session = None
    if session_id:
        existing_session = db.query(StudySession).filter(
            StudySession.id == session_id,
            StudySession.user_id == user.id,
            StudySession.study_mode == user.study_mode,
        ).first()

    updated = False
    if existing_session:
        existing_session.subject = subject.strip()
        existing_session.duration_minutes = round(duration / 60, 2)
        existing_session.session_type = session_type
        if validated_exam_id:
            existing_session.exam_id = validated_exam_id
        if validated_project_id:
            existing_session.project_id = validated_project_id
        updated = True
    else:
        session = StudySession(
            subject=subject.strip(),
            duration_minutes=round(duration / 60, 2),
            user_id=user.id,
            session_type=session_type,
            exam_id=validated_exam_id,
            project_id=validated_project_id,
            study_mode=user.study_mode,
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
            subj = db.query(Subject).filter(Subject.id == sid, Subject.user_id == user.id).first()
            if subj:
                scheduled_subject_names.append(subj.name)

        studied_today = set()
        today_sessions = db.query(StudySession).filter(
            StudySession.user_id == user.id,
            StudySession.study_mode == user.study_mode,
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

    try:
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse(content={"error": "Erro ao salvar"}, status_code=500)

    return JSONResponse(content={"success": True, "day_completed": day_completed, "updated": updated})


@router.delete("/delete/{session_id}")
async def delete_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == user.id,
    ).first()

    if not session:
        return JSONResponse(content={"error": "Sessao nao encontrada"}, status_code=404)

    db.delete(session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse(content={"error": "Erro ao excluir"}, status_code=500)

    return JSONResponse(content={"success": True})


@router.post("/edit/{session_id}")
async def edit_session(
    request: Request,
    session_id: int,
    subject: str = Form(...),
    duration_minutes: float = Form(...),
    session_type: str = Form("estudo"),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == user.id,
    ).first()

    if not session:
        return JSONResponse(content={"error": "Sessao nao encontrada"}, status_code=404)

    if not subject or not subject.strip():
        return JSONResponse(content={"error": "Materia obrigatoria"}, status_code=400)

    if duration_minutes < 0:
        return JSONResponse(content={"error": "Duracao invalida"}, status_code=400)

    if session_type not in ("estudo", "teoria", "exercicios", "revisao", "projeto", "simulado"):
        session_type = "estudo"

    session.subject = subject.strip()
    session.duration_minutes = round(duration_minutes, 2)
    session.session_type = session_type

    try:
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse(content={"error": "Erro ao editar"}, status_code=500)

    return JSONResponse(content={
        "success": True,
        "session": {
            "id": session.id,
            "subject": session.subject,
            "duration_minutes": session.duration_minutes,
            "session_type": session.session_type,
        }
    })


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
    try:
        db.commit()
    except Exception:
        db.rollback()
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
        return JSONResponse(content={"day_completed": True, "has_schedule": False})

    scheduled_subject_ids = [e.subject_id for e in schedule_entries]
    scheduled_subject_names = []
    for sid in scheduled_subject_ids:
        subj = db.query(Subject).filter(Subject.id == sid, Subject.user_id == user.id).first()
        if subj:
            scheduled_subject_names.append(subj.name)

    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        func.date(StudySession.date) == today,
    ).all()
    studied_today = {s.subject for s in today_sessions}

    day_completed = len(scheduled_subject_names) > 0 and set(scheduled_subject_names) == studied_today

    return JSONResponse(content={"day_completed": day_completed, "has_schedule": True})


@router.get("/ping")
async def timer_ping():
    return JSONResponse(content={"status": "ok"})


@router.post("/save-state")
async def save_timer_state(
    request: Request,
    seconds: int = Form(...),
    subject: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    user.timer_state_seconds = max(0, min(seconds, 86400))
    user.timer_state_subject = subject[:100] if subject else ""
    try:
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse(content={"error": "Erro ao salvar estado"}, status_code=500)

    return JSONResponse(content={"success": True})


@router.get("/get-state")
async def get_timer_state(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    return JSONResponse(content={
        "seconds": user.timer_state_seconds or 0,
        "subject": user.timer_state_subject or "",
    })


@router.post("/clear-state")
async def clear_timer_state(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"error": "unauthorized"}, status_code=401)

    user.timer_state_seconds = 0
    user.timer_state_subject = ""
    try:
        db.commit()
    except Exception:
        db.rollback()

    return JSONResponse(content={"success": True})


@router.get("/popup")
async def timer_popup(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return request.app.state.templates.TemplateResponse(
        request,
        "timer_popup.html",
        context={
            "study_mode": user.study_mode,
        },
    )
