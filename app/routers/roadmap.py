from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.phase import Phase
from app.services.phase_service import PhaseService
from app.services.goal_service import GoalService
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def roadmap(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    phase_service = PhaseService(db, user.id)
    goal_service = GoalService(db, user.id)

    phases = phase_service.get_all_phases()
    goals = goal_service.get_all_goals()

    goals_by_phase = {}
    for goal in goals:
        if goal.phase_id not in goals_by_phase:
            goals_by_phase[goal.phase_id] = []
        goals_by_phase[goal.phase_id].append(goal)

    return request.app.state.templates.TemplateResponse(
        request,
        "roadmap.html",
        context={
            "phases": phases,
            "goals_by_phase": goals_by_phase,
        },
    )


@router.post("/phase/create")
async def create_phase(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    order: int = Form(0),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    phase_service = PhaseService(db, user.id)
    phase_service.create_phase(name=name, description=description, order=order)
    return RedirectResponse(url="/roadmap", status_code=303)


@router.post("/phase/{phase_id}/delete")
async def delete_phase(phase_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    phase_service = PhaseService(db, user.id)
    phase_service.delete_phase(phase_id)
    return RedirectResponse(url="/roadmap", status_code=303)


@router.post("/goal/create")
async def create_goal(
    request: Request,
    title: str = Form(...),
    phase_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    phase = db.query(Phase).filter(Phase.id == phase_id, Phase.user_id == user.id).first()
    if not phase:
        return RedirectResponse(url="/roadmap", status_code=303)

    goal_service = GoalService(db, user.id)
    goal_service.create_goal(title=title, phase_id=phase_id)
    return RedirectResponse(url="/roadmap", status_code=303)


@router.post("/goal/{goal_id}/toggle")
async def toggle_goal(goal_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    goal_service = GoalService(db, user.id)
    goal_service.toggle_goal(goal_id)
    return RedirectResponse(url="/roadmap", status_code=303)


@router.post("/goal/{goal_id}/delete")
async def delete_goal(goal_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    goal_service = GoalService(db, user.id)
    goal_service.delete_goal(goal_id)
    return RedirectResponse(url="/roadmap", status_code=303)
