from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from app.database.connection import get_db
from app.services.dashboard_service import DashboardService
from app.services.phase_service import PhaseService
from app.services.calendar_service import CalendarService
from app.services.recommendation_service import RecommendationService
from app.services.domain_service import DomainService
from app.models.study_session import StudySession
from app.models.today_plan import TodayPlanItem
from app.models.subject import Subject
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dashboard_service = DashboardService(db, user.id, user.study_mode)
    phase_service = PhaseService(db, user.id, user.study_mode)
    calendar_service = CalendarService(db, user.id)
    rec_service = RecommendationService(db, user.id, user.study_mode)
    domain_service = DomainService(db, user.id, user.study_mode)

    dashboard_data = dashboard_service.get_dashboard_data()
    phases = phase_service.get_all_phases()
    current_streak = calendar_service.get_current_streak()

    today = datetime.now().date()

    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        func.date(StudySession.date) == today
    ).all()
    today_minutes = sum(s.duration_minutes for s in today_sessions)
    today_sessions_count = len(today_sessions)

    today_plan_items = db.query(TodayPlanItem).filter(
        TodayPlanItem.user_id == user.id,
        TodayPlanItem.study_mode == user.study_mode,
        TodayPlanItem.date == today
    ).order_by(TodayPlanItem.completed.asc(), TodayPlanItem.id.asc()).all()
    completed_plan_items = sum(1 for item in today_plan_items if item.completed)
    total_plan_items = len(today_plan_items)

    subjects = db.query(Subject).filter(
        Subject.user_id == user.id,
        Subject.study_mode == user.study_mode
    ).all()

    next_action = rec_service.get_next_action()
    weekly_report = rec_service.get_weekly_report()
    subjects_domain = domain_service.get_all_subjects_domain()

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
            "today_sessions_count": today_sessions_count,
            "today_plan_items": today_plan_items,
            "completed_plan_items": completed_plan_items,
            "total_plan_items": total_plan_items,
            "subjects": subjects,
            "next_action": next_action,
            "weekly_report": weekly_report,
            "subjects_domain": subjects_domain,
        },
    )
