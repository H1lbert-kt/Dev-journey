from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/help")
async def help_center(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return request.app.state.templates.TemplateResponse(
        request,
        "help.html",
        context={
            "user": user,
            "study_mode": user.study_mode or "programacao",
        },
    )
