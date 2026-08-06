from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.services.phase_service import PhaseService
from app.services.goal_service import GoalService
from app.services.project_service import ProjectService
from app.services.calendar_service import CalendarService
from app.models.study_session import StudySession
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def stats(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    phase_service = PhaseService(db, user.id)
    goal_service = GoalService(db, user.id)
    project_service = ProjectService(db, user.id)
    calendar_service = CalendarService(db, user.id)

    phases = phase_service.get_all_phases()
    all_goals = goal_service.get_all_goals()
    completed_goals = [g for g in all_goals if g.completed]
    completed_projects = project_service.get_completed_count()
    studied_days = calendar_service.get_total_studied_days()
    current_streak = calendar_service.get_current_streak()
    total_progress = 0.0

    if phases:
        total_progress = round(sum(p.progress for p in phases) / len(phases), 1)

    total_study_time = db.query(func.sum(StudySession.duration_minutes)).filter(
        StudySession.user_id == user.id
    ).scalar() or 0
    total_study_hours = round(total_study_time / 60, 1)

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        func.date(StudySession.date) == today
    ).all()
    today_minutes = sum(s.duration_minutes for s in today_sessions)

    yesterday_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        func.date(StudySession.date) == yesterday
    ).all()
    yesterday_minutes = sum(s.duration_minutes for s in yesterday_sessions)

    week_start = today - timedelta(days=today.weekday())
    week_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.date >= week_start
    ).all()
    week_minutes = sum(s.duration_minutes for s in week_sessions)

    month_start = today.replace(day=1)
    month_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.date >= month_start
    ).all()
    month_minutes = sum(s.duration_minutes for s in month_sessions)

    daily_avg = week_minutes / 7 if week_minutes > 0 else 0

    subject_stats = db.query(
        StudySession.subject,
        func.sum(StudySession.duration_minutes)
    ).filter(
        StudySession.user_id == user.id
    ).group_by(StudySession.subject).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "stats.html",
        context={
            "studied_days": studied_days,
            "current_streak": current_streak,
            "total_progress": total_progress,
            "completed_goals": len(completed_goals),
            "completed_projects": completed_projects,
            "phases": phases,
            "total_study_hours": total_study_hours,
            "today_minutes": round(today_minutes, 1),
            "yesterday_minutes": round(yesterday_minutes, 1),
            "week_minutes": round(week_minutes, 1),
            "month_minutes": round(month_minutes, 1),
            "daily_avg": round(daily_avg, 1),
            "subject_stats": subject_stats,
            "study_mode": user.study_mode,
        },
    )
