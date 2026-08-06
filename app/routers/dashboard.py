from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.database.connection import get_db
from app.services.dashboard_service import DashboardService
from app.services.phase_service import PhaseService
from app.services.calendar_service import CalendarService
from app.models.study_session import StudySession
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dashboard_service = DashboardService(db, user.id)
    phase_service = PhaseService(db, user.id)
    calendar_service = CalendarService(db, user.id)

    dashboard_data = dashboard_service.get_dashboard_data()
    phases = phase_service.get_all_phases()
    current_streak = calendar_service.get_current_streak()

    today = datetime.now().date()
    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        func.date(StudySession.date) == today
    ).all()
    today_minutes = sum(s.duration_minutes for s in today_sessions)

    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        context={
            "dashboard": dashboard_data,
            "phases": phases,
            "current_streak": current_streak,
            "study_mode": user.study_mode,
            "today_minutes": round(today_minutes, 1),
            "daily_goal": user.daily_goal_minutes,
        },
    )
