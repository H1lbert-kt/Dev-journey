from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.models.flashcard import Flashcard
from app.models.subject import Subject
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def flashcards_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    subjects = db.query(Subject).filter(Subject.user_id == user.id).all()
    flashcards = db.query(Flashcard).filter(Flashcard.user_id == user.id).all()
    due_cards = [f for f in flashcards if f.next_review and f.next_review <= datetime.now()]

    return request.app.state.templates.TemplateResponse(
        request,
        "flashcards.html",
        context={
            "subjects": subjects,
            "flashcards": flashcards,
            "due_cards": due_cards,
            "total_cards": len(flashcards),
        },
    )


@router.post("/create")
async def create_flashcard(
    request: Request,
    front: str = Form(...),
    back: str = Form(...),
    subject_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    flashcard = Flashcard(
        front=front,
        back=back,
        subject_id=subject_id,
        next_review=datetime.now(),
        user_id=user.id,
    )
    db.add(flashcard)
    db.commit()
    return RedirectResponse(url="/flashcards", status_code=303)


@router.post("/import")
async def import_flashcards(
    request: Request,
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    content = await file.read()
    text = content.decode("utf-8")
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    imported = 0
    for line in lines:
        parts = None
        if ";" in line:
            parts = line.split(";", 1)
        elif "\t" in line:
            parts = line.split("\t", 1)
        elif "|" in line:
            parts = line.split("|", 1)

        if parts and len(parts) == 2:
            front = parts[0].strip()
            back = parts[1].strip()
            if front and back:
                flashcard = Flashcard(
                    front=front,
                    back=back,
                    subject_id=subject_id,
        next_review=datetime.now(),
                    user_id=user.id,
                )
                db.add(flashcard)
                imported += 1

    db.commit()
    return RedirectResponse(url="/flashcards", status_code=303)


@router.post("/{card_id}/review")
async def review_flashcard(
    card_id: int,
    request: Request,
    quality: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    card = db.query(Flashcard).filter(Flashcard.id == card_id, Flashcard.user_id == user.id).first()
    if card:
        if quality >= 3:
            new_interval = card.interval_days * card.ease_factor
        else:
            new_interval = 1

        card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        card.interval_days = int(new_interval)
        card.next_review = datetime.now() + timedelta(days=card.interval_days)
        db.commit()

    return RedirectResponse(url="/flashcards", status_code=303)


@router.post("/{card_id}/delete")
async def delete_flashcard(card_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    card = db.query(Flashcard).filter(Flashcard.id == card_id, Flashcard.user_id == user.id).first()
    if card:
        db.delete(card)
        db.commit()
    return RedirectResponse(url="/flashcards", status_code=303)
