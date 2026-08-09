from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from app.database.connection import engine, Base, SessionLocal, DATABASE_URL, IS_POSTGRESQL
from app.config.settings import get_settings
from app.routers import dashboard, roadmap, projects, habits, calendar, stats, achievements, auth, timer, methods, subjects, flashcards, simulados, reviews

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

IS_PRODUCTION = os.environ.get("RENDER", False) or IS_POSTGRESQL


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info(f"Database: {'PostgreSQL (persistent)' if IS_POSTGRESQL else 'SQLite (ephemeral)'}")
    logger.info(f"Environment: {'Production' if IS_PRODUCTION else 'Development'}")
    logger.info("=" * 50)
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")

    db = SessionLocal()
    try:
        from app.models.user_session import UserSession
        deleted = db.query(UserSession).filter(UserSession.expires_at < datetime.now()).delete()
        db.commit()
        if deleted:
            logger.info(f"Cleaned up {deleted} expired sessions")
    except Exception as e:
        logger.warning(f"Session cleanup error: {e}")
    finally:
        db.close()

    yield
    logger.info("Shutting down application...")
    engine.dispose()


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
        path = request.url.path
        if path.startswith("/static") or path.startswith("/favicon"):
            return await call_next(request)

        request.state.study_mode = request.cookies.get("study_mode", "programacao")
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
    return {"status": "healthy", "version": "1.0.0", "database": "postgresql" if IS_POSTGRESQL else "sqlite"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=not IS_PRODUCTION)
