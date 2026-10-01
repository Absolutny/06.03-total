from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Payment, PaymentStatus, Subscription


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, subscription_id: int) -> Subscription | None:
        return self.db.get(Subscription, subscription_id)

    def list_by_client(self, client_id: int) -> list[Subscription]:
        return list(
            self.db.scalars(
                select(Subscription).where(Subscription.client_id == client_id).order_by(Subscription.end_date.desc())
            )
        )

    def find_usable(self, client_id: int, on_date: date) -> Subscription | None:
        """Действующий абонемент: активен, в сроке, есть остаток визитов (если они ограничены)."""
        stmt = (
            select(Subscription)
            .where(
                Subscription.client_id == client_id,
                Subscription.is_active.is_(True),
                Subscription.start_date <= on_date,
                Subscription.end_date >= on_date,
                (Subscription.visits_left.is_(None)) | (Subscription.visits_left > 0),
            )
            .order_by(Subscription.end_date)
        )
        return self.db.scalars(stmt).first()

    def add(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription

    def add_payment(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def revenue(self, start: datetime, end: datetime) -> tuple[float, int]:
        total, count = self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0), func.count(Payment.id)).where(
                Payment.status == PaymentStatus.PAID, Payment.created_at >= start, Payment.created_at < end
            )
        ).one()
        return float(total), int(count)
