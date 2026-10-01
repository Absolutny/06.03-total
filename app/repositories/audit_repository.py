from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: AuditLog) -> None:
        self.db.add(entry)

    def page(self, limit: int, offset: int) -> tuple[list[AuditLog], int]:
        total = self.db.scalar(select(func.count(AuditLog.id))) or 0
        items = list(self.db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)))
        return items, total
