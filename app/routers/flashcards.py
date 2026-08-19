from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database.connection import get_db
from app.models.flashcard import Flashcard, FlashcardReview
from app.models.subject import Subject
from app.routers.auth import require_auth
from app.services.flashcard_srs import (
    process_review, get_due_cards, get_flashcard_stats, get_card_state
)

router = APIRouter()

MAX_UPLOAD_SIZE = 1 * 1024 * 1024
MAX_IMPORT_LINES = 500


@router.get("/")
async def flashcards_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    stats = get_flashcard_stats(db, user.id, user.study_mode)
    subjects = db.query(Subject).filter(
        Subject.user_id == user.id, Subject.study_mode == user.study_mode
    ).all()
    flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user.id, Flashcard.study_mode == user.study_mode
    ).all()

    card_states = {card.id: get_card_state(card) for card in flashcards}

    return request.app.state.templates.TemplateResponse(
        request,
        "flashcards.html",
        context={
            "subjects": subjects,
            "flashcards": flashcards,
            "card_states": card_states,
            "stats": stats,
            "study_mode": user.study_mode,
        },
    )


@router.get("/review")
async def review_session(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    due_cards = get_due_cards(db, user.id, user.study_mode)

    if not due_cards:
        return request.app.state.templates.TemplateResponse(
            request,
            "flashcards.html",
            context={
                "subjects": db.query(Subject).filter(
                    Subject.user_id == user.id, Subject.study_mode == user.study_mode
                ).all(),
                "flashcards": db.query(Flashcard).filter(
                    Flashcard.user_id == user.id, Flashcard.study_mode == user.study_mode
                ).all(),
                "stats": get_flashcard_stats(db, user.id, user.study_mode),
                "study_mode": user.study_mode,
                "review_message": "Nenhum card para revisar no momento.",
            },
        )

    cards_data = []
    for card in due_cards:
        cards_data.append({
            "id": card.id,
            "front": card.front,
            "back": card.back,
            "subject": card.subject.name if card.subject else "Sem matéria",
            "subject_color": card.subject.color if card.subject else "#58a6ff",
            "state": get_card_state(card),
            "review_count": card.review_count,
        })

    return request.app.state.templates.TemplateResponse(
        request,
        "review_session.html",
        context={
            "cards": cards_data,
            "total": len(cards_data),
            "study_mode": user.study_mode,
        },
    )


@router.post("/api/review")
async def api_review_card(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Dados inválidos"}, status_code=400)

    card_id = body.get("card_id")
    quality = body.get("quality")

    if card_id is None or quality is None:
        return JSONResponse({"error": "card_id e quality são obrigatórios"}, status_code=400)

    try:
        card_id = int(card_id)
        quality = int(quality)
    except (ValueError, TypeError):
        return JSONResponse({"error": "Valores inválidos"}, status_code=400)

    if quality not in (0, 3, 4, 5):
        return JSONResponse({"error": "Quality deve ser 0, 3, 4 ou 5"}, status_code=400)

    card = db.query(Flashcard).filter(
        Flashcard.id == card_id,
        Flashcard.user_id == user.id,
        Flashcard.study_mode == user.study_mode,
    ).first()

    if not card:
        return JSONResponse({"error": "Card não encontrado"}, status_code=404)

    try:
        result = process_review(db, card, quality, user.id)
    except Exception:
        return JSONResponse({"error": "Erro ao processar revisão"}, status_code=500)

    return JSONResponse({
        "success": True,
        "quality": result["quality"],
        "interval_after": result["interval_after"],
        "next_review": result["next_review"].strftime("%d/%m/%Y"),
        "streak": result["streak"],
    })


@router.post("/api/review-batch")
async def api_review_batch(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Dados inválidos"}, status_code=400)

    reviews = body.get("reviews", [])
    if not reviews:
        return JSONResponse({"error": "Nenhuma revisão fornecida"}, status_code=400)

    results = []
    for r in reviews:
        card_id = r.get("card_id")
        quality = r.get("quality")
        if card_id is None or quality is None:
            continue
        try:
            card_id = int(card_id)
            quality = int(quality)
        except (ValueError, TypeError):
            continue

        card = db.query(Flashcard).filter(
            Flashcard.id == card_id,
            Flashcard.user_id == user.id,
            Flashcard.study_mode == user.study_mode,
        ).first()

        if not card:
            continue

        try:
            result = process_review(db, card, quality, user.id)
            results.append({"card_id": card_id, "success": True})
        except Exception:
            db.rollback()
            results.append({"card_id": card_id, "success": False})

    return JSONResponse({"processed": len(results), "results": results})


@router.get("/api/stats")
async def api_stats(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "Não autenticado"}, status_code=401)

    stats = get_flashcard_stats(db, user.id, user.study_mode)
    return JSONResponse(stats)


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

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == user.id,
        Subject.study_mode == user.study_mode,
    ).first()
    if not subject:
        return RedirectResponse(url="/flashcards", status_code=303)

    flashcard = Flashcard(
        front=front,
        back=back,
        subject_id=subject_id,
        user_id=user.id,
        study_mode=user.study_mode,
        next_review=datetime.now(),
    )
    db.add(flashcard)
    try:
        db.commit()
    except Exception:
        db.rollback()
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

    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.user_id == user.id,
        Subject.study_mode == user.study_mode,
    ).first()
    if not subject:
        return RedirectResponse(url="/flashcards", status_code=303)

    try:
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            return RedirectResponse(url="/flashcards", status_code=303)
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return RedirectResponse(url="/flashcards", status_code=303)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    lines = lines[:MAX_IMPORT_LINES]

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
                    user_id=user.id,
                    study_mode=user.study_mode,
                    next_review=datetime.now(),
                )
                db.add(flashcard)
                imported += 1

    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/flashcards", status_code=303)


@router.post("/{card_id}/delete")
async def delete_flashcard(card_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    card = db.query(Flashcard).filter(
        Flashcard.id == card_id,
        Flashcard.user_id == user.id,
        Flashcard.study_mode == user.study_mode,
    ).first()
    if card:
        db.delete(card)
        try:
            db.commit()
        except Exception:
            db.rollback()
    return RedirectResponse(url="/flashcards", status_code=303)
