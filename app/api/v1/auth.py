from fastapi import APIRouter, Depends, status

from app.api.deps import auth_service
from app.core.rate_limit import login_rate_limit
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest, LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse,
)
from app.security.dependencies import get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Регистрация клиента")
def register(data: RegisterRequest, service: AuthService = Depends(auth_service)):
    return service.register(data)


@router.post("/login", response_model=TokenResponse, summary="Вход: access + refresh токены",
             dependencies=[Depends(login_rate_limit)])
def login(data: LoginRequest, service: AuthService = Depends(auth_service)):
    return service.login(data)


@router.post("/refresh", response_model=TokenResponse, summary="Обновление пары токенов (refresh-токен одноразовый)")
def refresh(data: RefreshRequest, service: AuthService = Depends(auth_service)):
    return service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Выход: отзыв всех refresh-токенов")
def logout(user: User = Depends(get_current_user), service: AuthService = Depends(auth_service)):
    service.logout(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Смена пароля")
def change_password(data: ChangePasswordRequest, user: User = Depends(get_current_user),
                    service: AuthService = Depends(auth_service)):
    service.change_password(user, data)


@router.get("/me", response_model=UserResponse, summary="Текущий пользователь")
def me(user: User = Depends(get_current_user)):
    return user
