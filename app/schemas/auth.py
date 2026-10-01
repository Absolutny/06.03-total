from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Role
from app.security.passwords import validate_password_policy


def _clean(value: str) -> str:
    """Убираем управляющие символы и лишние пробелы; HTML не принимаем в именах."""
    value = "".join(ch for ch in value if ch.isprintable()).strip()
    if "<" in value or ">" in value:
        raise ValueError("Недопустимые символы")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9\- ()]{5,20}$")

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        error = validate_password_policy(v)
        if error:
            raise ValueError(error)
        return v

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = _clean(v)
        if len(v) < 2:
            raise ValueError("ФИО слишком короткое")
        return v


class CreateStaffRequest(RegisterRequest):
    role: Role

    @field_validator("role")
    @classmethod
    def _not_client(cls, v: Role) -> Role:
        if v == Role.CLIENT:
            raise ValueError("Для клиентов используйте /auth/register")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=2048)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password(cls, v: str) -> str:
        error = validate_password_policy(v)
        if error:
            raise ValueError(error)
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    phone: str | None
    role: Role
    is_active: bool
