from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.connection import get_db
from app.models.simulado import Simulado
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def simulados_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    simulados = db.query(Simulado).filter(Simulado.user_id == user.id).order_by(Simulado.created_at.desc()).all()

    total_questions = sum(s.total_questions for s in simulados)
    total_correct = sum(s.correct_answers for s in simulados)
    avg_score = round(total_correct / total_questions * 100, 1) if total_questions > 0 else 0
    total_time = sum(s.time_minutes for s in simulados)

    best_score = 0
    worst_score = 100
    for s in simulados:
        if s.total_questions > 0:
            score = round(s.correct_answers / s.total_questions * 100, 1)
            if score > best_score:
                best_score = score
            if score < worst_score:
                worst_score = score

    return request.app.state.templates.TemplateResponse(
        request,
        "simulados.html",
        context={
            "simulados": simulados,
            "total_questions": total_questions,
            "avg_score": avg_score,
            "total_time": round(total_time / 60, 1),
            "best_score": best_score,
            "worst_score": worst_score if simulados else 0,
        },
    )


@router.post("/create")
async def create_simulado(
    request: Request,
    name: str = Form(...),
    total_questions: int = Form(...),
    correct_answers: int = Form(...),
    time_minutes: float = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    score = round(correct_answers / total_questions * 100, 1) if total_questions > 0 else 0

    simulado = Simulado(
        name=name,
        total_questions=total_questions,
        correct_answers=correct_answers,
        time_minutes=time_minutes,
        score=score,
        user_id=user.id,
    )
    db.add(simulado)
    db.commit()
    return RedirectResponse(url="/simulados", status_code=303)


@router.post("/{simulado_id}/delete")
async def delete_simulado(simulado_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    simulado = db.query(Simulado).filter(Simulado.id == simulado_id, Simulado.user_id == user.id).first()
    if simulado:
        db.delete(simulado)
        db.commit()
    return RedirectResponse(url="/simulados", status_code=303)
