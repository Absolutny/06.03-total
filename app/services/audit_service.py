import re

from sqlalchemy.orm import Session

from app.core.context import client_ip
from app.models import AuditLog
from app.repositories.audit_repository import AuditRepository

_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


def _clean(value: str, limit: int) -> str:
    """Убираем переводы строк (защита от подделки записей журнала) и режем длину."""
    return _CONTROL.sub(" ", value)[:limit]


class AuditService:
    """Записывает события безопасности. Коммит выполняет вызывающий сервис."""

    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(self, event_type: str, description: str, user_id: int | None = None) -> None:
        self.repo.add(
            AuditLog(
                user_id=user_id,
                event_type=_clean(event_type, 32),
                description=_clean(description, 500),
                ip_address=client_ip.get(),
            )
        )

    def page(self, page: int, per_page: int):
        return self.repo.page(per_page, (page - 1) * per_page)
