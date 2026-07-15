"""Small route-aware fixed-window rate limiter."""

from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings


class RateLimitStore:
    """Process-local request timestamps, isolated behind a resettable API."""

    def __init__(self) -> None:
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        *,
        rule: str,
        client: str,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        cutoff = current - window_seconds
        key = (rule, client)
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, math.ceil(timestamps[0] + window_seconds - current))
                return False, retry_after
            timestamps.append(current)
        return True, 0

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = RateLimitStore()


def _rule_for(request: Request) -> tuple[str, int, int] | None:
    if request.method != "POST":
        return None

    settings = get_settings()
    path = request.url.path
    if path == "/auth/login":
        return "login", settings.rate_limit_login_per_minute, 60
    if path == "/marketing/demo-bookings":
        return "demo_booking", settings.rate_limit_login_per_minute, 60
    if path in {"/webhooks/moolre/payment", "/webhooks/moolre/ussd"} or path.startswith(
        "/ussdk/"
    ):
        return "webhook", settings.rate_limit_webhook_per_minute, 60
    if path in {"/communications/sms/broadcast", "/communications/sms/dues-reminder"}:
        return "sms", settings.rate_limit_sms_per_minute, 60
    if path == "/transactions/dues/collect":
        return "dues", settings.rate_limit_dues_per_minute, 60
    return None


class RouteRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        rule = _rule_for(request)
        if rule is None:
            return await call_next(request)

        name, limit, window_seconds = rule
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = rate_limiter.check(
            rule=name,
            client=client,
            limit=limit,
            window_seconds=window_seconds,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry later."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

