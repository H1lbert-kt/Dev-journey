from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import logging

from app.database.connection import get_db
from app.models.study_goal import StudyGoal
from app.models.exam import Exam
from app.routers.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def study_goal_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    active_goal = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == True,
    ).first()

    past_goals = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == False,
    ).order_by(StudyGoal.created_at.desc()).all()

    goal_days_until = None
    if active_goal and active_goal.target_date:
        goal_days_until = (active_goal.target_date - date.today()).days

    exams = db.query(Exam).filter(
        Exam.user_id == user.id,
        Exam.study_mode == user.study_mode,
    ).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "study_goal.html",
        context={
            "active_goal": active_goal,
            "past_goals": past_goals,
            "goal_days_until": goal_days_until,
            "exams": exams,
            "study_mode": user.study_mode,
        },
    )


@router.get("/api/active")
async def get_active_goal(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    from fastapi.responses import JSONResponse
    goal = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == True,
    ).first()

    if not goal:
        return JSONResponse({"active": False})

    days_until = None
    if goal.target_date:
        days_until = (goal.target_date - date.today()).days

    data = {
        "active": True,
        "id": goal.id,
        "goal_type": goal.goal_type,
        "title": goal.title,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "days_until": days_until,
    }

    if goal.goal_type == "concurso" and goal.exam_id:
        exam = db.query(Exam).filter(Exam.id == goal.exam_id).first()
        if exam:
            data["exam_name"] = exam.name
            data["exam_organization"] = exam.organization
            data["exam_position"] = exam.position

    if goal.goal_type == "vestibular":
        data["vestibular_name"] = goal.vestibular_name
        data["vestibular_institution"] = goal.vestibular_institution
        data["vestibular_course"] = goal.vestibular_course

    return JSONResponse(data)


@router.post("/create")
async def create_goal(
    request: Request,
    goal_type: str = Form("concurso"),
    title: str = Form(...),
    target_date: str = Form(""),
    exam_id: int = Form(0),
    vestibular_name: str = Form(""),
    vestibular_institution: str = Form(""),
    vestibular_course: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if goal_type not in ("concurso", "vestibular"):
        goal_type = "concurso"

    parsed_date = None
    if target_date:
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    existing_active = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == True,
    ).first()
    if existing_active:
        existing_active.active = False

    goal = StudyGoal(
        user_id=user.id,
        study_mode=user.study_mode,
        goal_type=goal_type,
        title=title.strip()[:200],
        target_date=parsed_date,
        exam_id=exam_id if exam_id > 0 else None,
        vestibular_name=vestibular_name.strip() or None,
        vestibular_institution=vestibular_institution.strip() or None,
        vestibular_course=vestibular_course.strip() or None,
        active=True,
    )
    db.add(goal)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(f"Failed to create study goal for user {user.id}")

    return RedirectResponse(url="/", status_code=303)


@router.post("/{goal_id}/deactivate")
async def deactivate_goal(goal_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.user_id == user.id,
    ).first()
    if goal:
        goal.active = False
        try:
            db.commit()
        except Exception:
            db.rollback()

    return RedirectResponse(url="/", status_code=303)


@router.post("/{goal_id}/delete")
async def delete_goal(goal_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    goal = db.query(StudyGoal).filter(
        StudyGoal.id == goal_id,
        StudyGoal.user_id == user.id,
    ).first()
    if goal:
        db.delete(goal)
        try:
            db.commit()
        except Exception:
            db.rollback()

    return RedirectResponse(url="/", status_code=303)
