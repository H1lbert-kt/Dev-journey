from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.connection import get_db
from app.models.simulado import Simulado
from app.models.study_goal import StudyGoal
from app.routers.auth import require_auth

router = APIRouter()


def _get_score(s):
    return s.score if s.score is not None else 0


def _get_points(s):
    if s.final_score is not None:
        return s.final_score
    return s.correct_answers if s.correction_method == "normal" else max(0, s.correct_answers - s.wrong_answers)


@router.get("/")
async def simulados_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    simulados = db.query(Simulado).filter(
        Simulado.user_id == user.id,
        Simulado.study_mode == user.study_mode
    ).order_by(
        Simulado.display_order.asc(),
        Simulado.created_at.desc()
    ).all()

    total_questions = sum(s.total_questions for s in simulados)
    total_correct = sum(s.correct_answers for s in simulados)
    avg_score = round(total_correct / total_questions * 100, 1) if total_questions > 0 else 0
    total_time = sum(s.time_minutes for s in simulados)

    best_score = 0
    worst_score = None
    for s in simulados:
        sc = _get_score(s)
        if s.total_questions > 0:
            if sc > best_score:
                best_score = sc
            if worst_score is None or sc < worst_score:
                worst_score = sc
    if worst_score is None:
        worst_score = 0

    last_simulado = simulados[0] if simulados else None

    active_goal = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == True,
    ).first()

    goal_simulados = []
    goal_avg = 0
    if active_goal and active_goal.exam_id:
        goal_simulados = [s for s in simulados if s.exam_id == active_goal.exam_id]
        if goal_simulados:
            goal_total = sum(s.total_questions for s in goal_simulados)
            goal_correct = sum(s.correct_answers for s in goal_simulados)
            goal_avg = round(goal_correct / goal_total * 100, 1) if goal_total > 0 else 0

    comparisons = {}
    for i in range(len(simulados)):
        curr = simulados[i]
        prev = simulados[i + 1] if i + 1 < len(simulados) else None
        if prev:
            curr_score = _get_score(curr)
            prev_score = _get_score(prev)
            diff = round(curr_score - prev_score, 1)
            comparisons[curr.id] = {"diff": diff}
        else:
            comparisons[curr.id] = {"diff": None}

    return request.app.state.templates.TemplateResponse(
        request,
        "simulados.html",
        context={
            "simulados": simulados,
            "comparisons": comparisons,
            "total_questions": total_questions,
            "avg_score": avg_score,
            "total_time": round(total_time / 60, 1),
            "best_score": best_score,
            "worst_score": worst_score if simulados else 0,
            "last_simulado": last_simulado,
            "active_goal": active_goal,
            "goal_simulados": goal_simulados,
            "goal_avg": goal_avg,
        },
    )


@router.get("/chart-data")
async def chart_data(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    simulados = db.query(Simulado).filter(
        Simulado.user_id == user.id,
        Simulado.study_mode == user.study_mode
    ).order_by(
        Simulado.display_order.asc(),
        Simulado.created_at.desc()
    ).all()

    labels = []
    scores = []
    normal_scores = []
    cespe_scores = []

    for s in simulados:
        labels.append(s.name)
        scores.append(_get_points(s))
        if s.correction_method == "cespe":
            cespe_scores.append(_get_points(s))
            normal_scores.append(None)
        else:
            normal_scores.append(_get_points(s))
            cespe_scores.append(None)

    avg_score = 0
    if simulados:
        total_points = sum(_get_points(s) for s in simulados)
        avg_score = round(total_points / len(simulados), 1)

    trend = "stable"
    if len(simulados) >= 2:
        recent = _get_points(simulados[0])
        prev = _get_points(simulados[1])
        diff = round(recent - prev, 1)
        if diff > 0:
            trend = "up"
        elif diff < 0:
            trend = "down"

    return JSONResponse({
        "labels": labels,
        "scores": scores,
        "normal_scores": normal_scores,
        "cespe_scores": cespe_scores,
        "avg_score": avg_score,
        "trend": trend,
        "count": len(simulados),
    })


@router.get("/chart-data/goal")
async def chart_data_goal(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    active_goal = db.query(StudyGoal).filter(
        StudyGoal.user_id == user.id,
        StudyGoal.study_mode == user.study_mode,
        StudyGoal.active == True,
    ).first()

    if not active_goal or not active_goal.exam_id:
        return JSONResponse({"count": 0, "avg_score": 0, "trend": "stable", "labels": [], "scores": []})

    simulados = db.query(Simulado).filter(
        Simulado.user_id == user.id,
        Simulado.study_mode == user.study_mode,
        Simulado.exam_id == active_goal.exam_id,
    ).order_by(
        Simulado.display_order.asc(),
        Simulado.created_at.desc()
    ).all()

    labels = []
    scores = []
    for s in simulados:
        labels.append(s.name)
        scores.append(_get_points(s))

    avg_score = 0
    if simulados:
        total_points = sum(_get_points(s) for s in simulados)
        avg_score = round(total_points / len(simulados), 1)

    trend = "stable"
    if len(simulados) >= 2:
        recent = _get_points(simulados[0])
        prev = _get_points(simulados[1])
        diff = round(recent - prev, 1)
        if diff > 0:
            trend = "up"
        elif diff < 0:
            trend = "down"

    return JSONResponse({
        "labels": labels,
        "scores": scores,
        "avg_score": avg_score,
        "trend": trend,
        "count": len(simulados),
    })


@router.post("/reorder")
async def reorder_simulados(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    order = body.get("order", [])
    if not isinstance(order, list) or len(order) > 200:
        return JSONResponse({"error": "Invalid order"}, status_code=400)

    for idx, simulado_id in enumerate(order):
        if not isinstance(simulado_id, int):
            continue
        simulado = db.query(Simulado).filter(
            Simulado.id == simulado_id,
            Simulado.user_id == user.id,
            Simulado.study_mode == user.study_mode
        ).first()
        if simulado:
            simulado.display_order = idx

    try:
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse({"error": "Failed to save order"}, status_code=500)

    return JSONResponse({"ok": True})


@router.post("/create")
async def create_simulado(
    request: Request,
    name: str = Form(...),
    total_questions: int = Form(...),
    correct_answers: int = Form(...),
    wrong_answers: int = Form(0),
    correction_method: str = Form("normal"),
    time_minutes: float = Form(0),
    time_minutes_manual: float = Form(0),
    exam_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if time_minutes <= 0 and time_minutes_manual > 0:
        time_minutes = time_minutes_manual

    if total_questions <= 0:
        return RedirectResponse(url="/simulados", status_code=303)
    if correct_answers < 0 or wrong_answers < 0:
        return RedirectResponse(url="/simulados", status_code=303)
    if correct_answers + wrong_answers > total_questions:
        return RedirectResponse(url="/simulados", status_code=303)
    if time_minutes < 0:
        return RedirectResponse(url="/simulados", status_code=303)
    if correction_method not in ("normal", "cespe"):
        correction_method = "normal"
    name = name.strip()
    if len(name) > 200:
        name = name[:200]

    null_answers = max(0, total_questions - correct_answers - wrong_answers)

    if correction_method == "cespe":
        final_score = max(0, correct_answers - wrong_answers)
        score = round(final_score / total_questions * 100, 1) if total_questions > 0 else 0
    else:
        final_score = correct_answers
        score = round(correct_answers / total_questions * 100, 1) if total_questions > 0 else 0

    max_order = db.query(func.max(Simulado.display_order)).filter(Simulado.user_id == user.id, Simulado.study_mode == user.study_mode).scalar()
    next_order = (max_order or 0) + 1

    simulado = Simulado(
        name=name,
        total_questions=total_questions,
        correct_answers=correct_answers,
        wrong_answers=wrong_answers,
        null_answers=null_answers,
        correction_method=correction_method,
        final_score=final_score,
        time_minutes=time_minutes,
        score=score,
        display_order=next_order,
        user_id=user.id,
        study_mode=user.study_mode,
        exam_id=exam_id if exam_id > 0 else None,
    )
    db.add(simulado)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(url="/simulados", status_code=303)


@router.post("/{simulado_id}/delete")
async def delete_simulado(simulado_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    simulado = db.query(Simulado).filter(Simulado.id == simulado_id, Simulado.user_id == user.id, Simulado.study_mode == user.study_mode).first()
    if simulado:
        db.delete(simulado)
        try:
            db.commit()
        except Exception:
            db.rollback()
    return RedirectResponse(url="/simulados", status_code=303)
