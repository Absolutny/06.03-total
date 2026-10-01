"""Глобальный обработчик ошибок: ни одно исключение не превращается в «голый» 500 с трассировкой."""
import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


def _body(status: int, code: str, message: str, details: dict[str, str] | None = None) -> dict:
    body = {"status": status, "code": code, "message": message, "timestamp": datetime.now().isoformat()}
    if details:
        body["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(_body(exc.status_code, exc.code, exc.message), status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        details: dict[str, str] = {}
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
            details[field or "request"] = str(err["msg"]).removeprefix("Value error, ")
        return JSONResponse(_body(422, "validation_error", "Ошибка валидации данных", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        return JSONResponse(_body(exc.status_code, "http_error", str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(IntegrityError)
    async def handle_integrity(_: Request, exc: IntegrityError):
        logger.warning("Нарушение целостности данных: %s", exc.orig)
        return JSONResponse(_body(409, "conflict", "Конфликт данных: запись уже существует или нарушена связь"), status_code=409)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Необработанная ошибка: %s %s", request.method, request.url.path)
        return JSONResponse(_body(500, "internal_error", "Внутренняя ошибка сервера"), status_code=500)
