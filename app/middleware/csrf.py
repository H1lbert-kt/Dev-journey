import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
import logging

logger = logging.getLogger(__name__)

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FIELD = "csrf_token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
EXEMPT_PATHS = {"/timer/ping", "/health", "/timer/save-state", "/timer/clear-state", "/timer/get-state"}


def _generate_token() -> str:
    return secrets.token_hex(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith("/static") or path.startswith("/favicon"):
            return await call_next(request)

        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if not request.cookies.get(CSRF_COOKIE):
                response.set_cookie(
                    CSRF_COOKIE, _generate_token(),
                    httponly=False, samesite="lax", max_age=86400,
                )
            return response

        if path in EXEMPT_PATHS:
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")

        form_token = ""
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            try:
                body = await request.body()
                import urllib.parse
                form_data = urllib.parse.parse_qs(body.decode("utf-8", errors="replace"))
                form_token = form_data.get(CSRF_FIELD, [""])[0]
            except Exception:
                pass

        if not cookie_token and not header_token and not form_token:
            logger.warning("CSRF token missing for %s %s", request.method, path)

        if cookie_token and header_token and cookie_token != header_token:
            logger.warning("CSRF token mismatch for %s %s", request.method, path)

        return await call_next(request)
