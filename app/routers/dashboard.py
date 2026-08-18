from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.services.dashboard_service import DashboardService
from app.services.phase_service import PhaseService
from app.services.calendar_service import CalendarService
from app.models.study_session import StudySession
from app.models.today_plan import TodayPlanItem
from app.models.subject import Subject
from app.models.study_goal import StudyGoal
from app.models.simulado import Simulado
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

    dashboard_data = dashboard_service.get_dashboard_data()
    phases = phase_service.get_all_phases()
    current_streak = calendar_service.get_current_streak()

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    today_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        func.date(StudySession.date) == today
    ).all()
    today_minutes = sum(s.duration_minutes for s in today_sessions)

    today_sessions_count = len(today_sessions)

    week_start = today - timedelta(days=today.weekday())
    week_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        StudySession.date >= week_start
    ).all()
    week_minutes = sum(s.duration_minutes for s in week_sessions)

    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    last_week_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        StudySession.date >= last_week_start,
        StudySession.date <= last_week_end
    ).all()
    last_week_minutes = sum(s.duration_minutes for s in last_week_sessions)

    yesterday_sessions = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode,
        func.date(StudySession.date) == yesterday
    ).all()
    yesterday_minutes = sum(s.duration_minutes for s in yesterday_sessions)

    subject_today = {}
    for s in today_sessions:
        subject_today[s.subject] = subject_today.get(s.subject, 0) + s.duration_minutes
    most_studied_subject = ""
    most_studied_minutes = 0
    if subject_today:
        for subj, mins in subject_today.items():
            if mins > most_studied_minutes:
                most_studied_subject = subj
                most_studied_minutes = mins

    last_session = None
    last_session_data = db.query(StudySession).filter(
        StudySession.user_id == user.id,
        StudySession.study_mode == user.study_mode
    ).order_by(StudySession.date.desc()).first()
    if last_session_data:
        last_session = {
            "subject": last_session_data.subject,
            "duration": last_session_data.duration_minutes,
            "date": last_session_data.date,
        }

    today_plan_items = db.query(TodayPlanItem).filter(
        TodayPlanItem.user_id == user.id,
        TodayPlanItem.study_mode == user.study_mode,
        TodayPlanItem.date == today
    ).all()
    completed_plan_items = sum(1 for item in today_plan_items if item.completed)
    total_plan_items = len(today_plan_items)

    avg_daily = week_minutes / max(1, today.weekday() + 1) if week_minutes > 0 else 0
    week_pct = ((week_minutes - last_week_minutes) / last_week_minutes * 100) if last_week_minutes > 0 else 0

    subjects = db.query(Subject).filter(Subject.user_id == user.id, Subject.study_mode == user.study_mode).all()

    active_goal = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == True,
    ).first()

    weak_subjects = []
    if subjects:
        subject_scores = {}
        for subj in subjects:
            subj_sessions = [s for s in today_sessions + week_sessions if s.subject == subj.name]
            if subj_sessions:
                avg_dur = sum(s.duration_minutes for s in subj_sessions) / len(subj_sessions)
                subject_scores[subj.name] = avg_dur
        if subject_scores:
            sorted_subjects = sorted(subject_scores.items(), key=lambda x: x[1])
            weak_subjects = [{"name": n, "minutes": round(m, 1)} for n, m in sorted_subjects[:3]]

    recommendation = None
    if weak_subjects and user.daily_goal_minutes > 0:
        weakest = weak_subjects[0]
        if today_minutes < user.daily_goal_minutes:
            recommendation = {
                "subject": weakest["name"],
                "message": f"{weakest['name']} esta com menor desempenho. Considere uma sessao de 45 min.",
            }

    goal_days_until = None
    if active_goal and active_goal.target_date:
        from datetime import date as date_type
        goal_days_until = (active_goal.target_date - date_type.today()).days

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
            "week_minutes": round(week_minutes, 1),
            "last_week_minutes": round(last_week_minutes, 1),
            "yesterday_minutes": round(yesterday_minutes, 1),
            "most_studied_subject": most_studied_subject,
            "last_session": last_session,
            "today_plan_items": today_plan_items,
            "completed_plan_items": completed_plan_items,
            "total_plan_items": total_plan_items,
            "avg_daily": round(avg_daily, 1),
            "week_pct": round(week_pct, 1),
            "subjects": subjects,
            "active_goal": active_goal,
            "goal_days_until": goal_days_until,
            "weak_subjects": weak_subjects,
            "recommendation": recommendation,
        },
    )
