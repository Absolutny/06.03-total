from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models import Payment, PaymentStatus, Role, Subscription, User
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.subscription import RevenueReport, SubscriptionIssue
from app.services.audit_service import AuditService


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SubscriptionRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    def my(self, client: User) -> list[Subscription]:
        return self.repo.list_by_client(client.id)

    def issue(self, data: SubscriptionIssue, actor: User) -> Subscription:
        client = self.users.get(data.client_id)
        if client is None or client.role != Role.CLIENT:
            raise ResourceNotFoundError("Клиент не найден")

        today = date.today()
        subscription = self.repo.add(
            Subscription(
                client_id=client.id,
                type=data.type,
                visits_left=data.visits,  # None = безлимит по числу визитов
                start_date=today,
                end_date=today + timedelta(days=data.duration_days),
                is_active=True,
            )
        )
        self.repo.add_payment(
            Payment(client_id=client.id, subscription_id=subscription.id, amount=data.amount,
                    status=PaymentStatus.PAID, created_by=actor.id)
        )
        self.audit.log("SUBSCRIPTION_ISSUED", f"Абонемент {data.type} клиенту #{client.id}, {data.amount} руб.", actor.id)
        self.db.commit()
        return subscription

    def revenue(self, date_from: date, date_to: date) -> RevenueReport:
        start = datetime.combine(date_from, time.min)
        end = datetime.combine(date_to + timedelta(days=1), time.min)
        total, count = self.repo.revenue(start, end)
        return RevenueReport(date_from=date_from, date_to=date_to, total_revenue=total, payments_count=count)
