from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.models.achievement import Achievement
from app.models.study_session import StudySession
from app.models.project import Project
from app.models.simulado import Simulado
from app.models.calendar_day import CalendarDay
from app.models.exam import Exam
from app.services.achievement_service import AchievementService
from app.routers.auth import require_auth

router = APIRouter()

AUTO_ACHIEVEMENTS = [
    {"name": "Primeira Sessao", "description": "Completou sua primeira sessao de estudo", "icon": "&#128218;", "check": "first_session"},
    {"name": "1 Hora Estudada", "description": "Acumulou 1 hora de estudo", "icon": "&#9200;", "check": "one_hour"},
    {"name": "10 Horas Estudadas", "description": "Acumulou 10 horas de estudo", "icon": "&#128293;", "check": "ten_hours"},
    {"name": "50 Horas Estudadas", "description": "Acumulou 50 horas de estudo", "icon": "&#127942;", "check": "fifty_hours"},
    {"name": "7 Dias Consecutivos", "description": "Estudou 7 dias seguidos", "icon": "&#128293;", "check": "streak_7"},
    {"name": "30 Dias Consecutivos", "description": "Estudou 30 dias seguidos", "icon": "&#127775;", "check": "streak_30"},
    {"name": "Primeiro Simulado", "description": "Realizou seu primeiro simulado", "icon": "&#128220;", "check": "first_simulado"},
    {"name": "Primeiro Projeto", "description": "Cadastrou seu primeiro projeto", "icon": "&#128640;", "check": "first_project"},
    {"name": "Primeiro Concurso", "description": "Cadastrou seu primeiro concurso", "icon": "&#127963;", "check": "first_exam"},
]


def check_auto_achievements(user_id, db, study_mode=None):
    """Check and unlock auto-achievements based on user data."""
    achievements = db.query(Achievement).filter(
        Achievement.user_id == user_id
    ).all()
    existing_names = {a.name for a in achievements}
    newly_unlocked = []

    for auto in AUTO_ACHIEVEMENTS:
        if auto["name"] in existing_names:
            continue

        should_unlock = False

        if auto["check"] == "first_session":
            q = db.query(func.count(StudySession.id)).filter(StudySession.user_id == user_id)
            if study_mode:
                q = q.filter(StudySession.study_mode == study_mode)
            count = q.scalar()
            should_unlock = count >= 1
        elif auto["check"] == "one_hour":
            q = db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0)).filter(StudySession.user_id == user_id)
            if study_mode:
                q = q.filter(StudySession.study_mode == study_mode)
            total = q.scalar()
            should_unlock = total >= 60
        elif auto["check"] == "ten_hours":
            q = db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0)).filter(StudySession.user_id == user_id)
            if study_mode:
                q = q.filter(StudySession.study_mode == study_mode)
            total = q.scalar()
            should_unlock = total >= 600
        elif auto["check"] == "fifty_hours":
            q = db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0)).filter(StudySession.user_id == user_id)
            if study_mode:
                q = q.filter(StudySession.study_mode == study_mode)
            total = q.scalar()
            should_unlock = total >= 3000
        elif auto["check"] == "streak_7":
            streak = _get_streak(user_id, db)
            should_unlock = streak >= 7
        elif auto["check"] == "streak_30":
            streak = _get_streak(user_id, db)
            should_unlock = streak >= 30
        elif auto["check"] == "first_simulado":
            q = db.query(func.count(Simulado.id)).filter(Simulado.user_id == user_id)
            if study_mode:
                q = q.filter(Simulado.study_mode == study_mode)
            count = q.scalar()
            should_unlock = count >= 1
        elif auto["check"] == "first_project":
            q = db.query(func.count(Project.id)).filter(Project.user_id == user_id)
            if study_mode:
                q = q.filter(Project.study_mode == study_mode)
            count = q.scalar()
            should_unlock = count >= 1
        elif auto["check"] == "first_exam":
            q = db.query(func.count(Exam.id)).filter(Exam.user_id == user_id)
            if study_mode:
                q = q.filter(Exam.study_mode == study_mode)
            count = q.scalar()
            should_unlock = count >= 1

        if should_unlock:
            achievement = Achievement(
                name=auto["name"],
                description=auto["description"],
                icon=auto["icon"],
                unlocked=True,
                unlocked_at=datetime.now(),
                user_id=user_id,
            )
            db.add(achievement)
            newly_unlocked.append(auto["name"])

    if newly_unlocked:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return newly_unlocked


def _get_streak(user_id, db):
    """Calculate current streak of consecutive study days."""
    today = datetime.now().date()
    streak = 0
    check_date = today

    while streak < 1000:
        day = db.query(CalendarDay).filter(
            CalendarDay.user_id == user_id,
            CalendarDay.date == check_date,
            CalendarDay.studied == True
        ).first()

        if day:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak


@router.get("/")
async def achievements(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.initialize_default_achievements()
    check_auto_achievements(user.id, db, study_mode=user.study_mode)

    achievements = db.query(Achievement).filter(
        Achievement.user_id == user.id
    ).order_by(Achievement.unlocked.desc(), Achievement.created_at.desc()).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "achievements.html",
        context={
            "achievements": achievements,
            "study_mode": user.study_mode,
        },
    )


@router.post("/{achievement_id}/unlock")
async def unlock_achievement(achievement_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.unlock_achievement(achievement_id)
    return RedirectResponse(url="/achievements", status_code=303)


@router.post("/create")
async def create_achievement(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.create_achievement(name=name, description=description, icon=icon)
    return RedirectResponse(url="/achievements", status_code=303)


@router.post("/{achievement_id}/delete")
async def delete_achievement(achievement_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.delete_achievement(achievement_id)
    return RedirectResponse(url="/achievements", status_code=303)
