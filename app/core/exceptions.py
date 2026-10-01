"""Доменные исключения. Транслируются в HTTP-ответы глобальным обработчиком."""


class AppError(Exception):
    status_code = 400
    code = "app_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ResourceNotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthorized"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"


class SlotIsFullError(ConflictError):
    code = "slot_is_full"


class NoActiveSubscriptionError(AppError):
    status_code = 402
    code = "no_active_subscription"


class RateLimitError(AppError):
    status_code = 429
    code = "too_many_requests"
