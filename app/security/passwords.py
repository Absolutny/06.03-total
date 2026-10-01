"""Хеширование паролей: BCrypt со случайной солью + политика сложности."""
import re

import bcrypt

from app.config import get_settings

MAX_BYTES = 72  # ограничение алгоритма BCrypt

# Хеш-«пустышка»: проверяется, если пользователь не найден (выравнивает время ответа)
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt(get_settings().bcrypt_rounds)).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:MAX_BYTES], bcrypt.gensalt(get_settings().bcrypt_rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:MAX_BYTES], password_hash.encode())
    except ValueError:
        return False


def verify_dummy(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def validate_password_policy(password: str) -> str | None:
    """Возвращает текст ошибки или None, если пароль подходит."""
    if len(password.encode()) > MAX_BYTES:
        return "Пароль не должен превышать 72 байта."
    if len(password) < 8:
        return "Пароль должен содержать не менее 8 символов."
    if not re.search(r"[A-ZА-ЯЁ]", password):
        return "Пароль должен содержать заглавную букву."
    if not re.search(r"[a-zа-яё]", password):
        return "Пароль должен содержать строчную букву."
    if not re.search(r"\d", password):
        return "Пароль должен содержать цифру."
    return None
