from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
import logging

from app.database.connection import get_db
from app.models.exam import Exam, ExamSubject
from app.models.study_session import StudySession
from app.models.simulado import Simulado
from app.models.subject import Subject
from app.models.calendar_day import CalendarDay
from app.routers.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


def _compute_exam_stats(exam, db, user_id):
    today = date.today()
    days_until = None
    if exam.exam_date:
        delta = (exam.exam_date - today).days
        days_until = delta

    exam_subjects = db.query(ExamSubject).filter(ExamSubject.exam_id == exam.id).all()

    avg_progress = 0.0
    weighted_progress = 0.0
    if exam_subjects:
        total_weight = sum(s.weight for s in exam_subjects)
        progress_sum = sum(s.progress for s in exam_subjects)
        avg_progress = round(progress_sum / len(exam_subjects), 1)
        if total_weight > 0:
            weighted_progress = round(sum(s.progress * s.weight for s in exam_subjects) / total_weight, 1)

    total_minutes = db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0.0)).filter(
        StudySession.exam_id == exam.id,
        StudySession.user_id == user_id,
    ).scalar()

    sessions_count = db.query(func.count(StudySession.id)).filter(
        StudySession.exam_id == exam.id,
        StudySession.user_id == user_id,
    ).scalar()

    return {
        "days_until": days_until,
        "avg_progress": avg_progress,
        "weighted_progress": weighted_progress,
        "total_minutes": round(total_minutes, 1),
        "sessions_count": sessions_count,
        "subject_count": len(exam_subjects),
    }


STATUS_LABELS = {
    "planejando": "Planejando",
    "estudando": "Estudando",
    "inscrito": "Inscrito",
    "prova_realizada": "Prova Realizada",
    "finalizado": "Finalizado",
}


@router.get("/")
async def exams_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exams = db.query(Exam).filter(Exam.user_id == user.id).order_by(Exam.created_at.desc()).all()

    exams_data = []
    for exam in exams:
        stats = _compute_exam_stats(exam, db, user.id)
        exam_subjects = db.query(ExamSubject).filter(ExamSubject.exam_id == exam.id).all()
        exams_data.append({
            "exam": exam,
            "stats": stats,
            "subjects": exam_subjects,
            "status_label": STATUS_LABELS.get(exam.status, exam.status),
        })

    studying_count = sum(1 for e in exams if e.status == "estudando")

    next_exam = None
    next_days = None
    today = date.today()
    for exam in exams:
        if exam.exam_date and exam.exam_date >= today and exam.status not in ("prova_realizada", "finalizado"):
            delta = (exam.exam_date - today).days
            if next_days is None or delta < next_days:
                next_days = delta
                next_exam = exam

    return request.app.state.templates.TemplateResponse(
        request,
        "exams.html",
        context={
            "exams": exams_data,
            "total_exams": len(exams),
            "studying_count": studying_count,
            "next_exam": next_exam,
            "next_days": next_days,
            "today": date.today(),
            "study_mode": user.study_mode,
        },
    )


@router.post("/create")
async def create_exam(
    request: Request,
    name: str = Form(...),
    organization: str = Form(""),
    position: str = Form(""),
    banca: str = Form(""),
    status: str = Form("planejando"),
    exam_date: str = Form(""),
    salary: str = Form(""),
    vacancies: int = Form(0),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    parsed_date = None
    if exam_date:
        try:
            parsed_date = datetime.strptime(exam_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if status not in STATUS_LABELS:
        status = "planejando"

    exam = Exam(
        name=name.strip(),
        organization=organization.strip() or None,
        position=position.strip() or None,
        banca=banca.strip() or None,
        status=status,
        exam_date=parsed_date,
        salary=salary.strip() or None,
        vacancies=vacancies if vacancies > 0 else None,
        notes=notes.strip() or None,
        user_id=user.id,
    )
    db.add(exam)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(f"Failed to create exam for user {user.id}")
    return RedirectResponse(url="/exams", status_code=303)


@router.post("/{exam_id}/update")
async def update_exam(
    exam_id: int,
    request: Request,
    name: str = Form(...),
    organization: str = Form(""),
    position: str = Form(""),
    banca: str = Form(""),
    status: str = Form("planejando"),
    exam_date: str = Form(""),
    salary: str = Form(""),
    vacancies: int = Form(0),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first()
    if not exam:
        return RedirectResponse(url="/exams", status_code=303)

    parsed_date = None
    if exam_date:
        try:
            parsed_date = datetime.strptime(exam_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if status not in STATUS_LABELS:
        status = "planejando"

    exam.name = name.strip()
    exam.organization = organization.strip() or None
    exam.position = position.strip() or None
    exam.banca = banca.strip() or None
    exam.status = status
    exam.exam_date = parsed_date
    exam.salary = salary.strip() or None
    exam.vacancies = vacancies if vacancies > 0 else None
    exam.notes = notes.strip() or None

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(f"Failed to update exam {exam_id} for user {user.id}")
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)


@router.post("/{exam_id}/delete")
async def delete_exam(exam_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first()
    if exam:
        try:
            db.query(StudySession).filter(
                StudySession.exam_id == exam_id,
                StudySession.user_id == user.id,
            ).update({StudySession.exam_id: None})
            db.delete(exam)
            db.commit()
        except Exception:
            db.rollback()
            logger.warning(f"Failed to delete exam {exam_id} for user {user.id}")
    return RedirectResponse(url="/exams", status_code=303)


@router.get("/{exam_id}")
async def exam_detail(exam_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first()
    if not exam:
        return RedirectResponse(url="/exams", status_code=303)

    exam_subjects = db.query(ExamSubject).filter(ExamSubject.exam_id == exam.id).order_by(ExamSubject.name).all()
    user_subjects = db.query(Subject).filter(Subject.user_id == user.id).order_by(Subject.name).all()

    stats = _compute_exam_stats(exam, db, user.id)

    study_sessions = db.query(StudySession).filter(
        StudySession.exam_id == exam.id,
        StudySession.user_id == user.id,
    ).order_by(StudySession.date.desc()).all()

    simulados = db.query(Simulado).filter(Simulado.user_id == user.id).order_by(Simulado.created_at.desc()).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "exam_detail.html",
        context={
            "exam": exam,
            "exam_subjects": exam_subjects,
            "user_subjects": user_subjects,
            "stats": stats,
            "study_sessions": study_sessions,
            "simulados": simulados,
            "today": date.today(),
            "status_label": STATUS_LABELS.get(exam.status, exam.status),
            "study_mode": user.study_mode,
        },
    )


@router.post("/{exam_id}/subject/create")
async def create_exam_subject(
    exam_id: int,
    request: Request,
    name: str = Form(...),
    weight: float = Form(1.0),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first()
    if not exam:
        return RedirectResponse(url="/exams", status_code=303)

    if weight < 0:
        weight = 1.0

    subject = ExamSubject(
        exam_id=exam_id,
        name=name.strip(),
        weight=weight,
        progress=0.0,
    )
    db.add(subject)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(f"Failed to create exam subject for exam {exam_id}")
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)


@router.post("/{exam_id}/subject/{subject_id}/update")
async def update_exam_subject(
    exam_id: int,
    subject_id: int,
    request: Request,
    name: str = Form(...),
    weight: float = Form(1.0),
    progress: float = Form(0.0),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first()
    if not exam:
        return RedirectResponse(url="/exams", status_code=303)

    subject = db.query(ExamSubject).filter(
        ExamSubject.id == subject_id,
        ExamSubject.exam_id == exam_id,
    ).first()
    if not subject:
        return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

    subject.name = name.strip() or subject.name
    subject.weight = max(0, weight)
    subject.progress = max(0.0, min(100.0, progress))

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(f"Failed to update exam subject {subject_id}")
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)


@router.post("/{exam_id}/subject/{subject_id}/delete")
async def delete_exam_subject(
    exam_id: int,
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.user_id == user.id).first()
    if not exam:
        return RedirectResponse(url="/exams", status_code=303)

    subject = db.query(ExamSubject).filter(
        ExamSubject.id == subject_id,
        ExamSubject.exam_id == exam_id,
    ).first()
    if subject:
        try:
            db.delete(subject)
            db.commit()
        except Exception:
            db.rollback()
            logger.warning(f"Failed to delete exam subject {subject_id}")
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)
