"""Фабрики сервисов для внедрения зависимостей (DI)."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.booking_service import BookingService
from app.services.hall_service import HallService
from app.services.schedule_service import ScheduleService
from app.services.subscription_service import SubscriptionService


def auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def hall_service(db: Session = Depends(get_db)) -> HallService:
    return HallService(db)


def schedule_service(db: Session = Depends(get_db)) -> ScheduleService:
    return ScheduleService(db)


def booking_service(db: Session = Depends(get_db)) -> BookingService:
    return BookingService(db)


def subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(db)


def audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)
