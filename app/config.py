"""Конфигурация приложения. Все значения читаются из переменных окружения."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_SECRET = "change-me-in-production-please-use-32-bytes-min"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "АИС «СпортКомплекс»"
    app_version: str = "2.0.0"
    environment: str = "development"  # development | production | test

    database_url: str = "sqlite:///./sport.db"

    # --- JWT ---
    jwt_secret: str = _INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    bcrypt_rounds: int = 12
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    # --- CORS: явный список разрешённых источников, через запятую ---
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # --- Rate limiting ---
    rate_limit_per_minute: int = 100
    login_rate_limit_per_minute: int = 5

    # --- Начальный администратор (создаётся, если пользователей нет) ---
    admin_email: str = "admin@complex.com"
    admin_password: str | None = None
    seed_demo_data: bool = False

    @field_validator("jwt_secret")
    @classmethod
    def _secret_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET должен содержать не менее 32 символов")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def assert_production_safe(self) -> None:
        """В боевом режиме запрещаем запуск с секретом по умолчанию."""
        if self.is_production and self.jwt_secret == _INSECURE_DEFAULT_SECRET:
            raise RuntimeError("В production необходимо задать собственный JWT_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
