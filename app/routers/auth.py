from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import re
import logging
from app.database.connection import get_db
from app.models.user import User
from app.utils.auth import hash_password, verify_password, create_session, get_session, delete_session, sanitize_input
from app.config.settings import IS_RENDER

logger = logging.getLogger(__name__)

router = APIRouter()

USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def require_auth(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if not token:
        return None
    session = get_session(token, db)
    if not session:
        return None
    user = db.query(User).filter(User.id == session["user_id"]).first()
    return user


@router.get("/login")
async def login_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        request,
        "login.html",
        context={"error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    username = sanitize_input(username)
    if not username or len(username) < 3:
        return request.app.state.templates.TemplateResponse(
            request,
            "login.html",
            context={"error": "Usuario invalido"},
        )

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash, user.id, db):
        return request.app.state.templates.TemplateResponse(
            request,
            "login.html",
            context={"error": "Usuario ou senha invalidos"},
        )

    token = create_session(user.id, db)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session_token", token, httponly=True, secure=IS_RENDER, max_age=86400, samesite="lax")
    response.set_cookie("study_mode", user.study_mode, httponly=True, max_age=86400, samesite="lax")
    return response


@router.get("/register")
async def register_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        request,
        "register.html",
        context={"error": None},
    )


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    study_mode: str = Form("programacao"),
    db: Session = Depends(get_db),
):
    username = sanitize_input(username)
    email = sanitize_input(email)

    if not USERNAME_REGEX.match(username):
        return request.app.state.templates.TemplateResponse(
            request,
            "register.html",
            context={"error": "Usuario invalido (3-30 caracteres, apenas letras, numeros e _)"},
        )

    if not EMAIL_REGEX.match(email):
        return request.app.state.templates.TemplateResponse(
            request,
            "register.html",
            context={"error": "Email invalido"},
        )

    if len(password) < 6:
        return request.app.state.templates.TemplateResponse(
            request,
            "register.html",
            context={"error": "Senha deve ter no minimo 6 caracteres"},
        )

    if password != password_confirm:
        return request.app.state.templates.TemplateResponse(
            request,
            "register.html",
            context={"error": "As senhas nao coincidem"},
        )

    if study_mode not in ["programacao", "concursos", "vestibulares"]:
        study_mode = "programacao"

    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        return request.app.state.templates.TemplateResponse(
            request,
            "register.html",
            context={"error": "Usuario ou email ja cadastrado"},
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        study_mode=study_mode,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        return request.app.state.templates.TemplateResponse(
            request,
            "register.html",
            context={"error": "Usuario ou email ja cadastrado"},
        )

    token = create_session(user.id, db)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session_token", token, httponly=True, secure=IS_RENDER, max_age=86400, samesite="lax")
    response.set_cookie("study_mode", study_mode, httponly=True, max_age=86400, samesite="lax")
    return response


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token, db)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    response.delete_cookie("study_mode")
    return response


@router.post("/switch-mode")
async def switch_mode(
    request: Request,
    mode: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if mode not in ["programacao", "concursos", "vestibulares"]:
        mode = "programacao"

    user.study_mode = mode
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        return RedirectResponse(url="/", status_code=303)

    referer = request.headers.get("referer", "/")
    if not referer.startswith("/") or referer.startswith("//"):
        referer = "/"
    response = RedirectResponse(url=referer, status_code=303)
    response.set_cookie("study_mode", mode, httponly=True, max_age=86400, samesite="lax")
    return response


@router.get("/mode")
async def get_mode(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse(content={"mode": "programacao"})
    return JSONResponse(content={"mode": user.study_mode})
