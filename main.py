from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from collections import defaultdict
import asyncio
import logging
import os
import time

from app.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from app.database.connection import engine, Base, SessionLocal, IS_POSTGRESQL, init_database
from app.config.settings import get_settings, IS_RENDER
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import dashboard, roadmap, projects, habits, calendar, stats, achievements, auth, timer, methods, subjects, flashcards, simulados, reviews, schedule, exams, journal, today_plan, skills, history, help, study_goal

settings = get_settings()
IS_PRODUCTION = IS_RENDER or IS_POSTGRESQL


def _init_sentry():
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment="production" if IS_PRODUCTION else "development",
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            send_default_pii=False,
            before_send=_sentry_before_send,
        )
        logger.info("Sentry initialized")
    except ImportError:
        logger.warning("sentry-sdk not installed — run: pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.warning("Sentry init failed: %s", e)


def _sentry_before_send(event, hint):
    if "request" in event:
        event["request"].pop("cookies", None)
        event["request"].pop("headers", None)
    return event


_init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("Database: %s", "PostgreSQL" if IS_POSTGRESQL else "SQLite")
    logger.info("Environment: %s", "Production" if IS_PRODUCTION else "Development")
    logger.info("=" * 50)
    logger.info("Initializing database tables...")
    init_database()
    logger.info("Database tables initialized.")

    db = SessionLocal()
    try:
        from app.models.user_session import UserSession
        deleted = db.query(UserSession).filter(UserSession.expires_at < datetime.now()).delete()
        db.commit()
        if deleted:
            logger.info("Cleaned up %d expired sessions", deleted)
    except Exception as e:
        logger.warning("Session cleanup error: %s", e)
    finally:
        db.close()

    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)
            try:
                db = SessionLocal()
                from app.models.user_session import UserSession
                deleted = db.query(UserSession).filter(UserSession.expires_at < datetime.now()).delete()
                db.commit()
                if deleted:
                    logger.info("Periodic cleanup: removed %d expired sessions", deleted)
            except Exception as e:
                logger.warning("Periodic session cleanup error: %s", e)
            finally:
                db.close()

    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
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
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        return response


class StudyModeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path.startswith("/favicon"):
            return await call_next(request)

        study_mode = request.cookies.get("study_mode", "programacao")
        request.state.study_mode = study_mode if study_mode in ("programacao", "concursos", "vestibulares") else "programacao"
        response = await call_next(request)
        return response


_rate_limit_instances = []


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, login_limit=10, register_limit=5, general_limit=120):
        super().__init__(app)
        self.login_limit = login_limit
        self.register_limit = register_limit
        self.general_limit = general_limit
        self._requests = defaultdict(list)
        self._login_attempts = defaultdict(list)
        self._register_attempts = defaultdict(list)
        self._cleanup_interval = 300
        self._last_cleanup = time.time()
        _rate_limit_instances.append(self)

    def reset_limits(self):
        """Clear all rate limit state. Used in tests."""
        self._requests.clear()
        self._login_attempts.clear()
        self._register_attempts.clear()

    def _get_client_ip(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self):
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - 3600
        for key in list(self._login_attempts.keys()):
            self._login_attempts[key] = [t for t in self._login_attempts[key] if t > cutoff]
            if not self._login_attempts[key]:
                del self._login_attempts[key]
        for key in list(self._register_attempts.keys()):
            self._register_attempts[key] = [t for t in self._register_attempts[key] if t > cutoff]
            if not self._register_attempts[key]:
                del self._register_attempts[key]
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if not self._requests[key]:
                del self._requests[key]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path == "/health":
            return await call_next(request)

        self._cleanup_old_entries()
        client_ip = self._get_client_ip(request)
        now = time.time()

        if path == "/login" and request.method == "POST":
            self._login_attempts[client_ip].append(now)
            recent = [t for t in self._login_attempts[client_ip] if t > now - 900]
            self._login_attempts[client_ip] = recent
            if len(recent) > self.login_limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Muitas tentativas de login. Tente novamente mais tarde."},
                    headers={"Retry-After": "900"},
                )

        if path == "/register" and request.method == "POST":
            self._register_attempts[client_ip].append(now)
            recent = [t for t in self._register_attempts[client_ip] if t > now - 3600]
            self._register_attempts[client_ip] = recent
            if len(recent) > self.register_limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Muitas tentativas de registro. Tente novamente mais tarde."},
                    headers={"Retry-After": "3600"},
                )

        self._requests[client_ip].append(now)
        recent = [t for t in self._requests[client_ip] if t > now - 60]
        self._requests[client_ip] = recent
        if len(recent) > self.general_limit:
            return JSONResponse(
                status_code=429,
                content={"error": "Muitas requisições. Aguarde um momento."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StudyModeMiddleware)
app.add_middleware(RequestIdMiddleware)


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
app.include_router(schedule.router, prefix="/schedule", tags=["Schedule"])
app.include_router(exams.router, prefix="/exams", tags=["Exams"])
app.include_router(journal.router, prefix="/journal", tags=["Journal"])
app.include_router(today_plan.router, prefix="/today-plan", tags=["Today Plan"])
app.include_router(skills.router, prefix="/skills", tags=["Skills"])
app.include_router(history.router, prefix="/history", tags=["History"])
app.include_router(help.router, tags=["Help"])
app.include_router(study_goal.router, prefix="/study-goal", tags=["Study Goal"])


@app.get("/")
async def root():
    return RedirectResponse(url="/login", status_code=303)


@app.get("/health")
async def health_check():
    db_ok = False
    db_error = None
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        db_error = type(e).__name__
        logger.warning("Health check DB failed: %s", e)

    status = "healthy" if db_ok else "degraded"
    code = 200 if db_ok else 503

    result = {
        "status": status,
        "version": "1.0.0",
        "database": "postgresql" if IS_POSTGRESQL else "sqlite",
        "db_connected": db_ok,
    }
    if db_error:
        result["db_error"] = db_error

    return JSONResponse(content=result, status_code=code)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<h1>404</h1><p>Página não encontrada.</p>",
            status_code=404,
            headers=headers,
        )
    return JSONResponse(
        status_code=404,
        content={"error": "Não encontrado"},
        headers=headers,
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if request_id else {}
    return JSONResponse(
        status_code=405,
        content={"error": "Método não permitido"},
        headers=headers,
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=not IS_PRODUCTION)


# ============================================================
# TEMPORARY TEST ROUTE — REMOVE AFTER MONITORING VERIFICATION
# ============================================================
_TEST_SECRET = "8ef6d3df4bf51f175bc41a1c96e24e9a"

@app.get("/_test-monitoring")
async def _test_monitoring(token: str = ""):
    if token != _TEST_SECRET:
        return JSONResponse(status_code=404, content={"error": "not found"})
    raise RuntimeError("Teste do monitoring controller: erro proposital para verificar integracao Telegram + approval")

@app.get("/_test-sentry-telegram")
async def _test_sentry_telegram(token: str = ""):
    if token != _TEST_SECRET:
        return JSONResponse(status_code=404, content={"error": "not found"})
    raise RuntimeError("Sentry+Telegram test: controlled exception for integration verification")
# ============================================================
