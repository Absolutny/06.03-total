"""Создание и проверка JWT: короткоживущий access и отзываемый refresh."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings
from app.core.exceptions import AuthenticationError

ACCESS = "access"
REFRESH = "refresh"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


def create_access_token(user_id: int, role: str) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": ACCESS,
        "iat": _now(),
        "exp": _now() + timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Возвращает (токен, jti, срок действия)."""
    s = get_settings()
    jti = uuid.uuid4().hex
    expires = _now() + timedelta(days=s.refresh_token_days)
    payload = {"sub": str(user_id), "type": REFRESH, "jti": jti, "iat": _now(), "exp": expires}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), jti, expires


def decode_token(token: str, expected_type: str) -> dict:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Срок действия токена истёк") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Недействительный токен") from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError("Неверный тип токена")
    return payload
