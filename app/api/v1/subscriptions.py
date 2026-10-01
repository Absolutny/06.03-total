from fastapi import APIRouter, Depends, status

from app.api.deps import subscription_service
from app.models import User
from app.schemas.subscription import SubscriptionIssue, SubscriptionResponse
from app.security.dependencies import require_client, require_staff
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.get("/my", response_model=list[SubscriptionResponse], summary="Мои абонементы: остаток визитов и срок")
def my_subscriptions(client: User = Depends(require_client),
                     service: SubscriptionService = Depends(subscription_service)):
    return service.my(client)


@router.post("/issue", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED,
             summary="Продать/выдать абонемент клиенту (ADMIN/MANAGER)")
def issue_subscription(data: SubscriptionIssue, actor: User = Depends(require_staff),
                       service: SubscriptionService = Depends(subscription_service)):
    return service.issue(data, actor)
