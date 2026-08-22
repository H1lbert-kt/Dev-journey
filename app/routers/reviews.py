from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.models.flashcard import Flashcard
from app.routers.auth import require_auth
from app.services.flashcard_srs import get_due_cards, get_flashcard_stats

router = APIRouter()


@router.get("/")
async def reviews_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    stats = get_flashcard_stats(db, user.id, user.study_mode)
    due_cards = get_due_cards(db, user.id, user.study_mode)

    upcoming_reviews = []
    now = datetime.now()
    for days_ahead in [1, 7, 30]:
        review_date = now + timedelta(days=days_ahead)
        count = db.query(Flashcard).filter(
            Flashcard.user_id == user.id,
            Flashcard.study_mode == user.study_mode,
            Flashcard.next_review > now,
            Flashcard.next_review <= review_date,
        ).count()
        upcoming_reviews.append({"days": days_ahead, "count": count})

    subject_reviews = {}
    for card in due_cards:
        subject = card.subject.name if card.subject else "Sem matéria"
        if subject not in subject_reviews:
            subject_reviews[subject] = {"count": 0, "color": card.subject.color if card.subject else "#58a6ff"}
        subject_reviews[subject]["count"] += 1

    return request.app.state.templates.TemplateResponse(
        request,
        "reviews.html",
        context={
            "stats": stats,
            "due_cards": due_cards,
            "upcoming_reviews": upcoming_reviews,
            "subject_reviews": subject_reviews,
            "study_mode": user.study_mode,
        },
    )
