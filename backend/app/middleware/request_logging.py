from __future__ import annotations

import logging
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("backend.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        """Log each request path, status code, and latency.
        Wrap the downstream handler without changing the response."""
        started = perf_counter()
        response = await call_next(request)
        elapsed_ms = (perf_counter() - started) * 1000.0
        logger.info(
            "%s %s status=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
