import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response."""

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.HEADER_NAME, "")
        if not request_id:
            request_id = uuid.uuid4().hex
        request_id = request_id[:128]

        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers[self.HEADER_NAME] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        logger.info(
            "%s %s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            elapsed_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            },
        )

        return response
