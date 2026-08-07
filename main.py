from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from contextlib import asynccontextmanager
import logging
import os

from app.database.connection import engine, Base, SessionLocal
from app.config.settings import get_settings
from app.routers import dashboard, roadmap, projects, habits, calendar, stats, achievements, auth, timer, methods, subjects, flashcards, simulados, reviews

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

IS_PRODUCTION = os.environ.get("RENDER", False) or settings.DATABASE_URL.startswith("postgresql")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="DevJourney",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    lifespan=lifespan,
)

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

templates = Jinja2Templates(directory=APP_DIR / "templates")
app.state.templates = templates


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class StudyModeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("session_token")
        study_mode = "programacao"
        if token:
            from app.utils.auth import get_session
            session = get_session(token)
            if session:
                db = SessionLocal()
                try:
                    from app.models.user import User
                    user = db.query(User).filter(User.id == session["user_id"]).first()
                    if user:
                        study_mode = user.study_mode
                finally:
                    db.close()
        request.state.study_mode = study_mode
        response = await call_next(request)
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StudyModeMiddleware)

app.include_router(auth.router, tags=["Auth"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(roadmap.router, prefix="/roadmap", tags=["Roadmap"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(habits.router, prefix="/habits", tags=["Habits"])
app.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])
app.include_router(achievements.router, prefix="/achievements", tags=["Achievements"])
app.include_router(timer.router, prefix="/timer", tags=["Timer"])
app.include_router(methods.router, prefix="/methods", tags=["Methods"])
app.include_router(subjects.router, prefix="/subjects", tags=["Subjects"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["Flashcards"])
app.include_router(simulados.router, prefix="/simulados", tags=["Simulados"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])


@app.get("/")
async def root():
    return RedirectResponse(url="/login", status_code=303)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=not IS_PRODUCTION)
