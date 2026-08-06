from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.achievement_service import AchievementService
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def achievements(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievements = achievement_service.initialize_default_achievements()

    return request.app.state.templates.TemplateResponse(
        request,
        "achievements.html",
        context={
            "achievements": achievements,
        },
    )


@router.post("/{achievement_id}/unlock")
async def unlock_achievement(achievement_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.unlock_achievement(achievement_id)
    return RedirectResponse(url="/achievements", status_code=303)


@router.post("/create")
async def create_achievement(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    icon: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.create_achievement(name=name, description=description, icon=icon)
    return RedirectResponse(url="/achievements", status_code=303)


@router.post("/{achievement_id}/delete")
async def delete_achievement(achievement_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    achievement_service = AchievementService(db, user.id)
    achievement_service.delete_achievement(achievement_id)
    return RedirectResponse(url="/achievements", status_code=303)
