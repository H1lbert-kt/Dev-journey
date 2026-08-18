from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.project import Project
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def history(
    request: Request,
    db: Session = Depends(get_db),
    period: str = "all",
    subject: str = "",
    session_type: str = "",
    project_id: int = 0,
    exam_id: int = 0,
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    today = datetime.now().date()
    query = db.query(StudySession).filter(StudySession.user_id == user.id, StudySession.study_mode == user.study_mode)

    if period == "today":
        query = query.filter(func.date(StudySession.date) == today)
    elif period == "week":
        week_ago = today - timedelta(days=6)
        query = query.filter(func.date(StudySession.date) >= week_ago)
    elif period == "month":
        month_ago = today - timedelta(days=29)
        query = query.filter(func.date(StudySession.date) >= month_ago)

    if subject:
        query = query.filter(StudySession.subject == subject)

    if session_type:
        query = query.filter(StudySession.session_type == session_type)

    if project_id:
        query = query.filter(StudySession.project_id == project_id)

    if exam_id:
        query = query.filter(StudySession.exam_id == exam_id)

    sessions = query.order_by(StudySession.date.desc()).all()

    total_minutes = sum(s.duration_minutes for s in sessions)
    total_sessions = len(sessions)

    by_subject = {}
    for s in sessions:
        by_subject[s.subject] = by_subject.get(s.subject, 0) + s.duration_minutes
    by_subject = dict(sorted(by_subject.items(), key=lambda x: x[1], reverse=True))

    user_subjects = db.query(Subject).filter(Subject.user_id == user.id, Subject.study_mode == user.study_mode).all()
    user_exams = db.query(Exam).filter(Exam.user_id == user.id, Exam.study_mode == user.study_mode).all()
    user_projects = db.query(Project).filter(Project.user_id == user.id, Project.study_mode == user.study_mode).all()

    filters = {
        "period": period,
        "subject": subject,
        "session_type": session_type,
        "project_id": project_id,
        "exam_id": exam_id,
    }

    return request.app.state.templates.TemplateResponse(
        request,
        "history.html",
        context={
            "sessions": sessions,
            "total_minutes": round(total_minutes, 1),
            "total_sessions": total_sessions,
            "by_subject": by_subject,
            "subjects": user_subjects,
            "exams": user_exams,
            "projects": user_projects,
            "filters": filters,
            "study_mode": user.study_mode,
        },
    )
