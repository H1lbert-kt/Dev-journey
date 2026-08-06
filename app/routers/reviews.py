from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.models.flashcard import Flashcard
from app.models.study_session import StudySession
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def reviews_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    now = datetime.now()

    due_cards = db.query(Flashcard).filter(
        Flashcard.user_id == user.id,
        Flashcard.next_review <= now
    ).all()

    upcoming_reviews = []
    for days_ahead in [1, 7, 30]:
        review_date = now + timedelta(days=days_ahead)
        cards = db.query(Flashcard).filter(
            Flashcard.user_id == user.id,
            Flashcard.next_review > now,
            Flashcard.next_review <= review_date
        ).count()
        upcoming_reviews.append({"days": days_ahead, "count": cards})

    subject_reviews = {}
    for card in due_cards:
        subject = card.subject.name if card.subject else "Sem materia"
        if subject not in subject_reviews:
            subject_reviews[subject] = 0
        subject_reviews[subject] += 1

    return request.app.state.templates.TemplateResponse(
        request,
        "reviews.html",
        context={
            "due_cards": due_cards,
            "upcoming_reviews": upcoming_reviews,
            "subject_reviews": subject_reviews,
        },
    )
