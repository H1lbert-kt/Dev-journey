import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse

logger = logging.getLogger(__name__)

IS_PRODUCTION = bool(__import__("os").environ.get("RENDER"))


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handler that logs errors and returns safe responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            endpoint = request.url.path
            method = request.method

            logger.exception(
                "Unhandled exception on %s %s [request_id=%s]",
                method,
                endpoint,
                request_id,
            )

            sentry_event_id = None
            try:
                import sentry_sdk
                sentry_event_id = sentry_sdk.capture_exception(exc)
            except ImportError:
                pass

            try:
                from app.notifications.telegram import notify_error_async
                from datetime import datetime

                approval_id = uuid.uuid4().hex[:16]

                frames = getattr(exc, "__traceback__", None)
                frame_info = ""
                if frames:
                    tb = frames
                    while tb.tb_next:
                        tb = tb.tb_next
                    f = tb.tb_frame
                    frame_info = f"`{f.f_code.co_filename}:{tb.tb_lineno}` in `{f.f_code.co_name}`"

                environment = "production" if IS_PRODUCTION else "development"
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

                sentry_url = ""
                if sentry_event_id and IS_PRODUCTION:
                    import os
                    org = os.environ.get("SENTRY_ORG", "")
                    project = os.environ.get("SENTRY_PROJECT", "devjourney")
                    if org:
                        sentry_url = f"https://sentry.io/organizations/{org}/projects/{project}/events/{sentry_event_id}/"

                notify_error_async(
                    error_type=type(exc).__name__,
                    error_value=str(exc),
                    endpoint=endpoint,
                    level=method,
                    url=str(request.url),
                    environment=environment,
                    timestamp=timestamp,
                    frame_info=frame_info,
                    approval_id=approval_id,
                    sentry_url=sentry_url,
                )
            except Exception:
                pass

            if IS_PRODUCTION:
                return HTMLResponse(
                    content="<h1>Erro interno</h1><p>Ocorreu um erro inesperado. Tente novamente.</p>",
                    status_code=500,
                    headers={"X-Request-ID": request_id},
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal Server Error",
                        "detail": str(exc),
                        "type": type(exc).__name__,
                        "request_id": request_id,
                    },
                    headers={"X-Request-ID": request_id},
                )
