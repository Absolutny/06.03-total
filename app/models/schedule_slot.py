from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_slot_time_order"),
        CheckConstraint("max_clients > 0", name="ck_slot_max_clients_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    trainer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.id"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    max_clients: Mapped[int]
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    trainer = relationship("User", lazy="joined")
    hall = relationship("Hall", lazy="joined")
