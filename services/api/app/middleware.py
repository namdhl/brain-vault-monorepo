"""
Request logging middleware:
- Generates request_id for every request
- Logs structured entry + exit with duration_ms and status_code
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logging_config import set_request_id

logger = logging.getLogger("brainvault.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        set_request_id(rid)

        start = time.monotonic()
        logger.info(
            "request_start",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
            },
        )

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.monotonic() - start) * 1000)
            logger.error(
                "request_error",
                extra={
                    "request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise

        duration_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "request_end",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-Id"] = rid
        return response
