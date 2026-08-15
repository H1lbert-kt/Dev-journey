from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
from app.database.connection import get_db
from app.models.journal import JournalEntry
from app.models.project import Project
from app.models.subject import Subject
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def journal_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id
    ).order_by(JournalEntry.date.desc(), JournalEntry.id.desc()).all()

    projects = db.query(Project).filter(Project.user_id == user.id).all()
    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "journal.html",
        context={
            "entries": entries,
            "projects": projects,
            "subjects": subjects,
            "study_mode": user.study_mode,
            "today": date.today().isoformat(),
        },
    )


@router.post("/create")
async def create_entry(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    entry_date: str = Form(...),
    project_id: int = Form(0),
    subject_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        parsed_date = date.fromisoformat(entry_date)
    except ValueError:
        parsed_date = date.today()

    entry = JournalEntry(
        title=title.strip(),
        content=content.strip(),
        date=parsed_date,
        project_id=project_id if project_id else None,
        subject_id=subject_id if subject_id else None,
        user_id=user.id,
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/journal", status_code=303)


@router.post("/{entry_id}/update")
async def update_entry(
    entry_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    entry_date: str = Form(...),
    project_id: int = Form(0),
    subject_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.user_id == user.id
    ).first()
    if not entry:
        return RedirectResponse(url="/journal", status_code=303)

    try:
        parsed_date = date.fromisoformat(entry_date)
    except ValueError:
        parsed_date = entry.date

    entry.title = title.strip()
    entry.content = content.strip()
    entry.date = parsed_date
    entry.project_id = project_id if project_id else None
    entry.subject_id = subject_id if subject_id else None
    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/journal", status_code=303)


@router.post("/{entry_id}/delete")
async def delete_entry(entry_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.user_id == user.id
    ).first()
    if entry:
        db.delete(entry)
        try:
            db.commit()
        except Exception:
            db.rollback()
    return RedirectResponse(url="/journal", status_code=303)
