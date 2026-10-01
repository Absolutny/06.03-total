from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import SubscriptionType


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[SubscriptionType] = mapped_column(Enum(SubscriptionType, native_enum=False, length=50))
    visits_left: Mapped[int | None]
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
