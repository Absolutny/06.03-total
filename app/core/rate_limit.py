"""Ограничение частоты запросов (скользящее окно, в памяти процесса).

Для нескольких процессов/реплик замените хранилище на Redis.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.context import client_ip


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: int) -> int:
        """Регистрирует событие. Возвращает 0, если лимит не превышен, иначе секунды до повтора."""
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            while q and now - q[0] >= window:
                q.popleft()
            if len(q) >= limit:
                return max(1, int(window - (now - q[0])))
            q.append(now)
            if len(self._events) > 50_000:  # защита памяти
                for k in list(self._events)[:10_000]:
                    self._events.pop(k, None)
            return 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


limiter = SlidingWindowLimiter()


def get_client_ip(request: Request) -> str:
    """X-Forwarded-For намеренно не используется: его может подделать клиент.
    За обратным прокси запускайте uvicorn с --proxy-headers и --forwarded-allow-ips."""
    return request.client.host if request.client else "0.0.0.0"


def _too_many(retry_after: int) -> JSONResponse:
    from datetime import datetime

    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={
            "status": 429,
            "code": "too_many_requests",
            "message": "Слишком много запросов. Повторите попытку позже.",
            "timestamp": datetime.now().isoformat(),
        },
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Общий лимит на IP (по умолчанию 100 запросов в минуту)."""

    async def dispatch(self, request: Request, call_next):
        ip = get_client_ip(request)
        token = client_ip.set(ip)
        try:
            retry = limiter.hit(f"global:{ip}", get_settings().rate_limit_per_minute, 60)
            if retry:
                return _too_many(retry)
            return await call_next(request)
        finally:
            client_ip.reset(token)


def login_rate_limit(request: Request) -> None:
    """Зависимость для /auth/login: защита от перебора паролей (по умолчанию 5 попыток в минуту на IP)."""
    from app.core.exceptions import RateLimitError

    retry = limiter.hit(f"login:{get_client_ip(request)}", get_settings().login_rate_limit_per_minute, 60)
    if retry:
        raise RateLimitError(f"Слишком много попыток входа. Повторите через {retry} с.")
