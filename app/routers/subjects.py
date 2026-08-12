from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.subject import Subject
from app.models.weekly_schedule import WeeklySchedule
from app.routers.auth import require_auth
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def subjects_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "subjects.html",
        context={"subjects": subjects, "study_mode": user.study_mode},
    )


@router.post("/create")
async def create_subject(
    request: Request,
    name: str = Form(...),
    color: str = Form("#58a6ff"),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subject = Subject(name=name.strip(), color=color, user_id=user.id)
    db.add(subject)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(f"Failed to create subject for user {user.id}")
    return RedirectResponse(url="/subjects", status_code=303)


@router.post("/{subject_id}/delete")
async def delete_subject(subject_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == user.id).first()
    if subject:
        try:
            db.query(WeeklySchedule).filter(
                WeeklySchedule.subject_id == subject_id,
                WeeklySchedule.user_id == user.id,
            ).delete()
            db.delete(subject)
            db.commit()
        except Exception:
            db.rollback()
            logger.warning(f"Failed to delete subject {subject_id} for user {user.id}")
    return RedirectResponse(url="/subjects", status_code=303)
