from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.skill import Skill
from app.routers.auth import require_auth

router = APIRouter()

CATEGORIES = {
    "frontend": "Frontend",
    "backend": "Backend",
    "banco_dados": "Banco de Dados",
    "devops": "DevOps",
    "ferramentas": "Ferramentas",
    "geral": "Geral",
}


@router.get("/")
async def skills(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    all_skills = db.query(Skill).filter(Skill.user_id == user.id).order_by(Skill.name).all()

    categories = {key: [] for key in CATEGORIES}
    for skill in all_skills:
        cat = skill.category if skill.category in CATEGORIES else "geral"
        categories[cat].append(skill)

    return request.app.state.templates.TemplateResponse(
        request,
        "skills.html",
        context={
            "skills": all_skills,
            "categories": categories,
            "category_labels": CATEGORIES,
            "study_mode": user.study_mode,
        },
    )


@router.post("/create")
async def create_skill(
    request: Request,
    name: str = Form(...),
    category: str = Form("geral"),
    progress: float = Form(0.0),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if category not in CATEGORIES:
        category = "geral"

    progress = max(0.0, min(100.0, progress))

    skill = Skill(
        name=name.strip(),
        category=category,
        progress=progress,
        description=description.strip() if description else "",
        user_id=user.id,
    )
    db.add(skill)
    try:
        db.commit()
    except Exception:
        db.rollback()

    return RedirectResponse(url="/skills", status_code=303)


@router.post("/{skill_id}/update")
async def update_skill(
    skill_id: int,
    request: Request,
    name: str = Form(None),
    category: str = Form(None),
    progress: float = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == user.id).first()
    if not skill:
        return RedirectResponse(url="/skills", status_code=303)

    if name is not None:
        skill.name = name.strip()
    if category is not None and category in CATEGORIES:
        skill.category = category
    if progress is not None:
        skill.progress = max(0.0, min(100.0, progress))
    if description is not None:
        skill.description = description.strip()

    try:
        db.commit()
    except Exception:
        db.rollback()

    return RedirectResponse(url="/skills", status_code=303)


@router.post("/{skill_id}/delete")
async def delete_skill(skill_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == user.id).first()
    if skill:
        db.delete(skill)
        try:
            db.commit()
        except Exception:
            db.rollback()

    return RedirectResponse(url="/skills", status_code=303)
