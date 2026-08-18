from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.project_service import ProjectService
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def projects(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(db, user.id, user.study_mode)
    projects = project_service.get_all_projects()

    return request.app.state.templates.TemplateResponse(
        request,
        "projects.html",
        context={
            "projects": projects,
        },
    )


@router.post("/create")
async def create_project(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    technologies: str = Form(""),
    status: str = Form("not_started"),
    github_link: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(db, user.id, user.study_mode)
    project_service.create_project(
        name=name,
        description=description,
        technologies=technologies,
        status=status,
        github_link=github_link,
        notes=notes,
    )
    return RedirectResponse(url="/projects", status_code=303)


@router.post("/{project_id}/update")
async def update_project(
    project_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    technologies: str = Form(""),
    status: str = Form("not_started"),
    github_link: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(db, user.id, user.study_mode)
    project_service.update_project(
        project_id,
        {
            "name": name,
            "description": description,
            "technologies": technologies,
            "status": status,
            "github_link": github_link,
            "notes": notes,
        },
    )
    return RedirectResponse(url="/projects", status_code=303)


@router.post("/{project_id}/delete")
async def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(db, user.id, user.study_mode)
    project_service.delete_project(project_id)
    return RedirectResponse(url="/projects", status_code=303)
