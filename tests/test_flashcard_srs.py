import pytest
from datetime import datetime, timedelta
from app.services.flashcard_srs import (
    calculate_next_interval, process_review, get_card_state,
    get_due_cards, get_flashcard_stats, MAX_INTERVAL_DAYS, MIN_EASE_FACTOR
)


class TestCalculateNextInterval:
    def test_new_card_first_review_pass(self):
        interval, ease = calculate_next_interval(0, 2.5, 4)
        assert interval == 1
        assert ease >= 2.5

    def test_new_card_first_review_fail(self):
        interval, ease = calculate_next_interval(0, 2.5, 0)
        assert interval == 1
        assert ease < 2.5

    def test_pass_quality_grows_interval(self):
        interval, ease = calculate_next_interval(10, 2.5, 4)
        assert interval > 10

    def test_fail_quality_resets_interval(self):
        interval, ease = calculate_next_interval(30, 2.5, 0)
        assert interval == 1

    def test_hard_quality_grows_slightly(self):
        interval, ease = calculate_next_interval(10, 2.5, 3)
        assert interval >= 10

    def test_easy_quality_grows_more(self):
        i_good, _ = calculate_next_interval(10, 2.5, 4)
        i_easy, _ = calculate_next_interval(10, 2.5, 5)
        assert i_easy >= i_good

    def test_interval_capped_at_max(self):
        interval, _ = calculate_next_interval(300, 3.0, 5)
        assert interval <= MAX_INTERVAL_DAYS

    def test_interval_minimum_is_one(self):
        interval, _ = calculate_next_interval(1, 1.3, 0)
        assert interval >= 1

    def test_ease_minimum(self):
        _, ease = calculate_next_interval(1, 1.3, 0)
        assert ease >= MIN_EASE_FACTOR

    def test_quality_clamped_to_range(self):
        interval1, _ = calculate_next_interval(10, 2.5, -5)
        interval2, _ = calculate_next_interval(10, 2.5, 0)
        assert interval1 == interval2

        interval3, _ = calculate_next_interval(10, 2.5, 10)
        interval4, _ = calculate_next_interval(10, 2.5, 5)
        assert interval3 == interval4

    def test_high_quality_ease_increases(self):
        _, ease = calculate_next_interval(10, 2.5, 5)
        assert ease > 2.5

    def test_low_quality_ease_decreases(self):
        _, ease = calculate_next_interval(10, 2.5, 0)
        assert ease < 2.5

    def test_medium_quality_ease_decreases(self):
        _, ease = calculate_next_interval(10, 2.5, 3)
        assert ease < 2.5


class TestGetCardState:
    def test_new_card(self):
        class FakeCard:
            review_count = 0
            interval_days = 0
        assert get_card_state(FakeCard()) == "new"

    def test_learning_card(self):
        class FakeCard:
            review_count = 1
            interval_days = 3
        assert get_card_state(FakeCard()) == "learning"

    def test_review_card(self):
        class FakeCard:
            review_count = 3
            interval_days = 14
        assert get_card_state(FakeCard()) == "review"

    def test_mature_card(self):
        class FakeCard:
            review_count = 10
            interval_days = 30
        assert get_card_state(FakeCard()) == "mature"


class TestProcessReview:
    def _make_card(self, db, user_id, study_mode="programacao"):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="Test Subject", user_id=user_id, study_mode=study_mode)
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(
            front="Q", back="A",
            subject_id=subject.id,
            user_id=user_id,
            study_mode=study_mode,
            ease_factor=2.5,
            interval_days=0,
            next_review=datetime.now(),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card

    def test_review_pass_updates_card(self, db, user_a):
        card = self._make_card(db, user_a.id)
        result = process_review(db, card, 4, user_a.id)
        assert result["quality"] == 4
        assert result["interval_after"] >= 1
        assert card.review_count == 1
        assert card.streak == 1

    def test_review_fail_resets(self, db, user_a):
        card = self._make_card(db, user_a.id)
        card.interval_days = 30
        card.streak = 5
        db.commit()
        result = process_review(db, card, 0, user_a.id)
        assert result["interval_after"] == 1
        assert card.streak == 0

    def test_review_records_history(self, db, user_a):
        from app.models.flashcard import FlashcardReview
        card = self._make_card(db, user_a.id)
        process_review(db, card, 4, user_a.id)
        reviews = db.query(FlashcardReview).filter(FlashcardReview.flashcard_id == card.id).all()
        assert len(reviews) == 1
        assert reviews[0].quality == 4

    def test_review_clamps_quality(self, db, user_a):
        card = self._make_card(db, user_a.id)
        result = process_review(db, card, 10, user_a.id)
        assert result["quality"] == 5

        result2 = process_review(db, card, -3, user_a.id)
        assert result2["quality"] == 0

    def test_consecutive_passes_increase_streak(self, db, user_a):
        card = self._make_card(db, user_a.id)
        process_review(db, card, 4, user_a.id)
        assert card.streak == 1
        process_review(db, card, 5, user_a.id)
        assert card.streak == 2

    def test_fail_resets_streak(self, db, user_a):
        card = self._make_card(db, user_a.id)
        process_review(db, card, 4, user_a.id)
        process_review(db, card, 5, user_a.id)
        assert card.streak == 2
        process_review(db, card, 0, user_a.id)
        assert card.streak == 0


class TestGetDueCards:
    def _make_card(self, db, user_id, review_count=0, interval_days=0, next_review=None, study_mode="programacao"):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="Test", user_id=user_id, study_mode=study_mode)
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(
            front="Q", back="A",
            subject_id=subject.id,
            user_id=user_id,
            study_mode=study_mode,
            interval_days=interval_days,
            next_review=next_review or datetime.now(),
            review_count=review_count,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card

    def test_returns_due_cards(self, db, user_a):
        card = self._make_card(db, user_a.id, next_review=datetime.now() - timedelta(hours=1))
        due = get_due_cards(db, user_a.id, "programacao")
        assert len(due) == 1
        assert due[0].id == card.id

    def test_excludes_future_cards(self, db, user_a):
        self._make_card(db, user_a.id, next_review=datetime.now() + timedelta(days=5))
        due = get_due_cards(db, user_a.id, "programacao")
        assert len(due) == 0

    def test_excludes_other_study_mode(self, db, user_a):
        self._make_card(db, user_a.id, study_mode="concursos", next_review=datetime.now() - timedelta(hours=1))
        due = get_due_cards(db, user_a.id, "programacao")
        assert len(due) == 0

    def test_overdue_before_new(self, db, user_a):
        new_card = self._make_card(db, user_a.id, review_count=0, next_review=datetime.now() - timedelta(hours=1))
        overdue_card = self._make_card(db, user_a.id, review_count=3, interval_days=10, next_review=datetime.now() - timedelta(days=5))
        due = get_due_cards(db, user_a.id, "programacao")
        assert len(due) == 2
        assert due[0].id == overdue_card.id
        assert due[1].id == new_card.id


class TestGetFlashcardStats:
    def _make_card(self, db, user_id, review_count=0, interval_days=0, next_review=None, study_mode="programacao"):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="Test", user_id=user_id, study_mode=study_mode)
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(
            front="Q", back="A",
            subject_id=subject.id,
            user_id=user_id,
            study_mode=study_mode,
            interval_days=interval_days,
            next_review=next_review or datetime.now(),
            review_count=review_count,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card

    def test_empty_stats(self, db, user_a):
        stats = get_flashcard_stats(db, user_a.id, "programacao")
        assert stats["total"] == 0
        assert stats["due"] == 0

    def test_counts_new_cards(self, db, user_a):
        self._make_card(db, user_a.id, review_count=0)
        self._make_card(db, user_a.id, review_count=0)
        stats = get_flashcard_stats(db, user_a.id, "programacao")
        assert stats["new_count"] == 2

    def test_counts_due_cards(self, db, user_a):
        self._make_card(db, user_a.id, next_review=datetime.now() - timedelta(hours=1))
        self._make_card(db, user_a.id, next_review=datetime.now() + timedelta(days=5))
        stats = get_flashcard_stats(db, user_a.id, "programacao")
        assert stats["due"] == 1

    def test_study_mode_isolation(self, db, user_a):
        self._make_card(db, user_a.id, study_mode="programacao")
        self._make_card(db, user_a.id, study_mode="concursos")
        stats = get_flashcard_stats(db, user_a.id, "programacao")
        assert stats["total"] == 1


class TestFlashcardReviewEndpoint:
    def _setup(self, db, user_a):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="Test Subj", user_id=user_a.id, study_mode="programacao")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(
            front="Pergunta?", back="Resposta!",
            subject_id=subject.id, user_id=user_a.id,
            study_mode="programacao", next_review=datetime.now(),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card

    def test_review_endpoint_returns_json(self, auth_client_a, db, user_a):
        card = self._setup(db, user_a)
        resp = auth_client_a.post("/flashcards/api/review", json={
            "card_id": card.id, "quality": 4
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_review_endpoint_rejects_unauthenticated(self, client):
        resp = client.post("/flashcards/api/review", json={
            "card_id": 1, "quality": 4
        })
        assert resp.status_code == 401

    def test_review_endpoint_rejects_invalid_quality(self, auth_client_a, db, user_a):
        card = self._setup(db, user_a)
        resp = auth_client_a.post("/flashcards/api/review", json={
            "card_id": card.id, "quality": 2
        })
        assert resp.status_code == 400

    def test_review_endpoint_rejects_other_users_card(self, auth_client_a, auth_client_b, db, user_a, user_b):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="B's Subj", user_id=user_b.id, study_mode="concursos")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(
            front="Q", back="A",
            subject_id=subject.id, user_id=user_b.id,
            study_mode="concursos", next_review=datetime.now(),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        resp = auth_client_a.post("/flashcards/api/review", json={
            "card_id": card.id, "quality": 4
        })
        assert resp.status_code == 404

    def test_review_endpoint_persists(self, auth_client_a, db, user_a):
        from app.models.flashcard import FlashcardReview
        card = self._setup(db, user_a)
        auth_client_a.post("/flashcards/api/review", json={
            "card_id": card.id, "quality": 4
        })
        reviews = db.query(FlashcardReview).filter(FlashcardReview.flashcard_id == card.id).all()
        assert len(reviews) == 1

    def test_double_click_no_duplicate(self, auth_client_a, db, user_a):
        from app.models.flashcard import FlashcardReview
        card = self._setup(db, user_a)
        auth_client_a.post("/flashcards/api/review", json={
            "card_id": card.id, "quality": 4
        })
        auth_client_a.post("/flashcards/api/review", json={
            "card_id": card.id, "quality": 4
        })
        reviews = db.query(FlashcardReview).filter(FlashcardReview.flashcard_id == card.id).all()
        assert len(reviews) == 2


class TestFlashcardCreation:
    def test_create_flashcard(self, auth_client_a, db, user_a):
        from app.models.subject import Subject
        subject = Subject(name="Create Test", user_id=user_a.id, study_mode="programacao")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        resp = auth_client_a.post("/flashcards/create", data={
            "front": "What is Python?",
            "back": "A programming language",
            "subject_id": subject.id,
        }, follow_redirects=False)
        assert resp.status_code == 303

    def test_flashcard_starts_as_new(self, auth_client_a, db, user_a):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="New Test", user_id=user_a.id, study_mode="programacao")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        auth_client_a.post("/flashcards/create", data={
            "front": "Q", "back": "A", "subject_id": subject.id,
        }, follow_redirects=False)
        card = db.query(Flashcard).filter(
            Flashcard.front == "Q",
            Flashcard.user_id == user_a.id,
        ).first()
        assert card is not None
        assert card.review_count == 0
        assert card.interval_days == 0
        assert card.ease_factor == 2.5


class TestDeleteFlashcard:
    def test_delete_own_flashcard(self, auth_client_a, db, user_a):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="Del Test", user_id=user_a.id, study_mode="programacao")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(front="Del", back="Me", subject_id=subject.id, user_id=user_a.id, study_mode="programacao")
        db.add(card)
        db.commit()
        db.refresh(card)
        resp = auth_client_a.post(f"/flashcards/{card.id}/delete", follow_redirects=False)
        assert resp.status_code == 303
        remaining = db.query(Flashcard).filter(Flashcard.id == card.id).first()
        assert remaining is None

    def test_cannot_delete_other_users_flashcard(self, auth_client_a, db, user_a, user_b):
        from app.models.flashcard import Flashcard
        from app.models.subject import Subject
        subject = Subject(name="B's Del", user_id=user_b.id, study_mode="concursos")
        db.add(subject)
        db.commit()
        db.refresh(subject)
        card = Flashcard(front="Not yours", back="Nope", subject_id=subject.id, user_id=user_b.id, study_mode="concursos")
        db.add(card)
        db.commit()
        db.refresh(card)
        resp = auth_client_a.post(f"/flashcards/{card.id}/delete", follow_redirects=False)
        remaining = db.query(Flashcard).filter(Flashcard.id == card.id).first()
        assert remaining is not None
