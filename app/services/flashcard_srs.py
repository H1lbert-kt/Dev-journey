"""
Spaced Repetition Service — SM-2 Algorithm Implementation

Algorithm: Modified SM-2 (SuperMemo 2)
Chosen for: simplicity, predictability, ease of maintenance, proven track record.

Quality ratings:
    0 = Errei  (complete blackout, no recall)
    3 = Difícil (correct with significant difficulty)
    4 = Bom     (correct with some hesitation)
    5 = Fácil   (perfect, instant recall)

Interval calculation:
    - If quality >= 3 (pass): interval = previous_interval * ease_factor
    - If quality < 3 (fail):  interval = 1 day (reset)

Ease factor update:
    EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    Minimum EF = 1.3

Constraints:
    - Maximum interval: 365 days
    - New cards start at interval=0, first review sets interval=1
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.flashcard import Flashcard, FlashcardReview

MAX_INTERVAL_DAYS = 365
MIN_EASE_FACTOR = 1.3


def calculate_next_interval(current_interval: int, current_ease: float, quality: int) -> tuple:
    """Calculate next interval and ease factor based on SM-2 algorithm.

    Returns: (new_interval_days, new_ease_factor)
    """
    quality = max(0, min(5, quality))

    if quality >= 3:
        if current_interval == 0:
            new_interval = 1
        else:
            new_interval = current_interval * current_ease
    else:
        new_interval = 1

    new_interval = min(int(new_interval), MAX_INTERVAL_DAYS)
    new_interval = max(1, new_interval)

    ease_delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ease = max(MIN_EASE_FACTOR, current_ease + ease_delta)

    return new_interval, new_ease


def process_review(db: Session, card: Flashcard, quality: int, user_id: int) -> dict:
    """Process a single flashcard review.

    1. Validates ownership
    2. Calculates new interval and ease factor
    3. Updates the flashcard
    4. Records the review in history
    5. Returns review result with next review date

    Returns dict with:
        - quality: the quality rating applied
        - interval_before: previous interval
        - interval_after: new interval
        - next_review: datetime of next review
        - ease_factor: new ease factor
        - streak: current streak
    """
    quality = max(0, min(5, quality))

    interval_before = card.interval_days
    ease_before = card.ease_factor

    new_interval, new_ease = calculate_next_interval(
        card.interval_days, card.ease_factor, quality
    )

    card.interval_days = new_interval
    card.ease_factor = new_ease
    card.next_review = datetime.now() + timedelta(days=new_interval)
    card.review_count += 1
    card.last_reviewed_at = datetime.now()

    if quality >= 3:
        card.streak += 1
    else:
        card.streak = 0

    review = FlashcardReview(
        flashcard_id=card.id,
        user_id=user_id,
        quality=quality,
        interval_before=interval_before,
        interval_after=new_interval,
        ease_factor_before=ease_before,
        ease_factor_after=new_ease,
        study_mode=card.study_mode,
        reviewed_at=datetime.now(),
    )
    db.add(review)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "quality": quality,
        "interval_before": interval_before,
        "interval_after": new_interval,
        "next_review": card.next_review,
        "ease_factor": new_ease,
        "streak": card.streak,
    }


def get_card_state(card: Flashcard) -> str:
    """Determine the display state of a flashcard.

    Returns: 'new', 'learning', 'review', or 'mature'
    """
    if card.review_count == 0:
        return "new"
    if card.interval_days < 7:
        return "learning"
    if card.interval_days < 21:
        return "review"
    return "mature"


def get_due_cards(db: Session, user_id: int, study_mode: str) -> list:
    """Get all flashcards due for review, ordered by priority.

    Priority:
    1. Overdue cards (most overdue first)
    2. New cards (never reviewed)
    3. Learning cards (interval < 7 days)
    """
    now = datetime.now()

    due = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.study_mode == study_mode,
        Flashcard.next_review <= now,
    ).all()

    overdue = [c for c in due if c.review_count > 0]
    new_cards = [c for c in due if c.review_count == 0]

    overdue.sort(key=lambda c: c.next_review or datetime.min)
    new_cards.sort(key=lambda c: c.created_at)

    return overdue + new_cards


def get_flashcard_stats(db: Session, user_id: int, study_mode: str) -> dict:
    """Compute flashcard statistics for the dashboard.

    Returns dict with:
        - total: total cards
        - new_count: never reviewed
        - learning: interval < 7 days
        - review: interval 7-21 days
        - mature: interval > 21 days
        - due: due for review now
        - overdue: past due
        - reviewed_today: reviewed today
        - reviewed_week: reviewed this week
        - accuracy: overall accuracy percentage
        - by_subject: dict of subject -> stats
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    all_cards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.study_mode == study_mode,
    ).all()

    total = len(all_cards)
    new_count = 0
    learning = 0
    review = 0
    mature = 0
    due = 0
    overdue = 0

    for card in all_cards:
        state = get_card_state(card)
        if state == "new":
            new_count += 1
        elif state == "learning":
            learning += 1
        elif state == "review":
            review += 1
        elif state == "mature":
            mature += 1

        if card.next_review and card.next_review <= now:
            due += 1
            if card.review_count > 0:
                overdue += 1

    from app.models.flashcard import FlashcardReview
    from sqlalchemy import func

    reviewed_today = db.query(FlashcardReview).filter(
        FlashcardReview.user_id == user_id,
        FlashcardReview.study_mode == study_mode,
        FlashcardReview.reviewed_at >= today_start,
    ).count()

    reviewed_week = db.query(FlashcardReview).filter(
        FlashcardReview.user_id == user_id,
        FlashcardReview.study_mode == study_mode,
        FlashcardReview.reviewed_at >= week_start,
    ).count()

    total_reviews = db.query(FlashcardReview).filter(
        FlashcardReview.user_id == user_id,
        FlashcardReview.study_mode == study_mode,
    ).count()

    correct_reviews = db.query(FlashcardReview).filter(
        FlashcardReview.user_id == user_id,
        FlashcardReview.study_mode == study_mode,
        FlashcardReview.quality >= 3,
    ).count()

    accuracy = (correct_reviews / total_reviews * 100) if total_reviews > 0 else 0

    by_subject = {}
    for card in all_cards:
        sname = card.subject.name if card.subject else "Sem matéria"
        if sname not in by_subject:
            by_subject[sname] = {
                "total": 0, "due": 0, "new": 0,
                "color": card.subject.color if card.subject else "#58a6ff",
                "subject_id": card.subject_id
            }
        by_subject[sname]["total"] += 1
        if card.next_review and card.next_review <= now:
            by_subject[sname]["due"] += 1
        if card.review_count == 0:
            by_subject[sname]["new"] += 1

    return {
        "total": total,
        "new_count": new_count,
        "learning": learning,
        "review": review,
        "mature": mature,
        "due": due,
        "overdue": overdue,
        "reviewed_today": reviewed_today,
        "reviewed_week": reviewed_week,
        "accuracy": round(accuracy, 1),
        "by_subject": by_subject,
    }
