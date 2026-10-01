"""FastAPI-зависимости: текущий пользователь и ролевой контроль (RBAC)."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.database import get_db
from app.models import Role, User
from app.security.jwt_service import ACCESS, decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthenticationError("Требуется авторизация")
    payload = decode_token(credentials.credentials, ACCESS)
    # Пользователь и роль проверяются по БД, а не берутся из токена на веру
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("Пользователь не найден или заблокирован")
    return user


def require_roles(*roles: Role):
    """Зависимость-фабрика: пропускает только перечисленные роли."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("Недостаточно прав для выполнения операции")
        return user

    return checker


require_admin = require_roles(Role.ADMIN)
require_staff = require_roles(Role.ADMIN, Role.MANAGER)
require_trainer = require_roles(Role.ADMIN, Role.TRAINER)
require_client = require_roles(Role.CLIENT)
