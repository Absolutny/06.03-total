import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.models import Role, User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, CreateStaffRequest, LoginRequest, RegisterRequest, TokenResponse
from app.security import jwt_service
from app.security.passwords import hash_password, verify_dummy, verify_password
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        self.audit = AuditService(db)

    # --- регистрация ---
    def register(self, data: RegisterRequest, role: Role = Role.CLIENT, actor_id: int | None = None) -> User:
        if self.users.get_by_email(data.email):
            raise ConflictError("Пользователь с таким email уже существует")
        user = self.users.add(
            User(
                email=data.email.lower(),
                password_hash=hash_password(data.password),
                full_name=data.full_name,
                phone=data.phone,
                role=role,
            )
        )
        if actor_id:
            self.audit.log("STAFF_CREATED", f"Создан сотрудник {user.email} ({role.value})", actor_id)
        else:
            self.audit.log("REGISTER", f"Зарегистрирован клиент {user.email}", user.id)
        self.db.commit()
        return user

    def create_staff(self, data: CreateStaffRequest, actor: User) -> User:
        return self.register(data, role=data.role, actor_id=actor.id)

    # --- вход ---
    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(data.email)
        if user is None:
            verify_dummy(data.password)  # одинаковое время ответа: нельзя угадать существование аккаунта
        if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
            self.audit.log("LOGIN_FAILED", f"Неудачный вход: {data.email}", user.id if user else None)
            self.db.commit()
            raise AuthenticationError("Неверный email или пароль")
        self.audit.log("LOGIN_SUCCESS", f"Вход пользователя {user.email} ({user.role})", user.id)
        tokens = self._issue_tokens(user)
        self.db.commit()
        return tokens

    # --- обновление токена (ротация refresh) ---
    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = jwt_service.decode_token(refresh_token, jwt_service.REFRESH)
        record = self.tokens.get_by_hash(jwt_service.hash_jti(payload["jti"]))
        user_id = int(payload["sub"])

        if record is None:
            raise AuthenticationError("Недействительный токен")
        if record.revoked:
            # Повторное использование отозванного токена = возможная кража: отзываем все сессии
            self.tokens.revoke_all_for_user(user_id)
            self.audit.log("REFRESH_REUSE", "Повторное использование refresh-токена", user_id)
            self.db.commit()
            raise AuthenticationError("Токен отозван. Войдите заново")
        if record.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise AuthenticationError("Срок действия токена истёк")

        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Пользователь не найден или заблокирован")

        record.revoked = True
        tokens = self._issue_tokens(user)
        self.db.commit()
        return tokens

    # --- смена пароля ---
    def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not verify_password(data.current_password, user.password_hash):
            self.audit.log("PASSWORD_CHANGE_FAILED", "Неверный текущий пароль", user.id)
            self.db.commit()
            raise AuthenticationError("Текущий пароль указан неверно")
        if data.current_password == data.new_password:
            raise ConflictError("Новый пароль должен отличаться от текущего")
        user.password_hash = hash_password(data.new_password)
        self.tokens.revoke_all_for_user(user.id)  # все прежние сессии становятся недействительными
        self.audit.log("PASSWORD_CHANGED", "Пользователь изменил пароль", user.id)
        self.db.commit()

    def logout(self, user: User) -> None:
        self.tokens.revoke_all_for_user(user.id)
        self.audit.log("LOGOUT", "Пользователь вышел из системы", user.id)
        self.db.commit()

    # --- внутреннее ---
    def _issue_tokens(self, user: User) -> TokenResponse:
        settings = get_settings()
        access = jwt_service.create_access_token(user.id, user.role)
        refresh, jti, expires = jwt_service.create_refresh_token(user.id)
        self.tokens.add(user.id, jwt_service.hash_jti(jti), expires)
        return TokenResponse(access_token=access, refresh_token=refresh, expires_in=settings.access_token_minutes * 60)
