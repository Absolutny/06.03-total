from datetime import date

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.deps import audit_service, auth_service, subscription_service
from app.core.exceptions import AppError
from app.models import User
from app.schemas.auth import CreateStaffRequest, UserResponse
from app.schemas.subscription import RevenueReport
from app.security.dependencies import require_admin
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class AuditEntry(BaseModel):
    id: int
    user_id: int | None
    event_type: str
    description: str
    ip_address: str | None
    timestamp: str


class AuditPage(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[AuditEntry]


@router.post("/staff", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Нанять сотрудника: TRAINER / MANAGER / ADMIN")
def create_staff(data: CreateStaffRequest, admin: User = Depends(require_admin),
                 service: AuthService = Depends(auth_service)):
    return service.create_staff(data, admin)


@router.get("/audit-logs", response_model=AuditPage, summary="Журнал аудита")
def audit_logs(page: int = Query(default=1, ge=1, le=10_000), per_page: int = Query(default=50, ge=1, le=200),
               _: User = Depends(require_admin), service: AuditService = Depends(audit_service)):
    items, total = service.page(page, per_page)
    return AuditPage(
        total=total, page=page, per_page=per_page,
        items=[AuditEntry(id=i.id, user_id=i.user_id, event_type=i.event_type, description=i.description,
                          ip_address=i.ip_address, timestamp=str(i.timestamp)) for i in items],
    )


@router.get("/reports/revenue", response_model=RevenueReport, summary="Выручка за период")
def revenue(date_from: date, date_to: date, _: User = Depends(require_admin),
            service: SubscriptionService = Depends(subscription_service)):
    if date_to < date_from:
        raise AppError("date_to не может быть раньше date_from")
    return service.revenue(date_from, date_to)
