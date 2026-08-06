from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path

from app.database.connection import engine, Base, SessionLocal
from app.routers import dashboard, roadmap, projects, habits, calendar, stats, achievements, auth, timer, methods, subjects, flashcards, simulados, reviews

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DevJourney", version="1.0.0")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
