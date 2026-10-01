import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, bookings, halls, schedule, subscriptions, trainer
from app.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401  (регистрация сущностей в metadata)
from app.seed import seed

logger = logging.getLogger(__name__)

DESCRIPTION = """
REST API системы управления спортивным комплексом.

**Авторизация:** `POST /api/v1/auth/login` → `access_token` → кнопка **Authorize** → вставить токен.

**Роли:** ADMIN, MANAGER, TRAINER, CLIENT.
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    get_settings().assert_production_safe()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    logger.info("Приложение запущено")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        docs_url="/swagger-ui.html",
        redoc_url=None,
        openapi_url="/v3/api-docs",
        lifespan=lifespan,
    )

    # Порядок: последний добавленный выполняется первым
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,  # явный список, никакого "*"
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    register_exception_handlers(app)

    for module in (auth, halls, schedule, bookings, subscriptions, trainer, admin):
        app.include_router(module.router)

    @app.get("/health", tags=["Service"], summary="Проверка работоспособности")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
