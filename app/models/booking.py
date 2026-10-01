from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import BookingStatus


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_slot_id: Mapped[int] = mapped_column(ForeignKey("schedule_slots.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus, native_enum=False, length=20), default=BookingStatus.BOOKED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    slot = relationship("ScheduleSlot", lazy="joined")
