from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, booking_id: int) -> Booking | None:
        return self.db.get(Booking, booking_id)

    def count_by_schedule_slot_id(self, slot_id: int) -> int:
        """Количество занятых мест (отменённые записи не считаются)."""
        return self.db.scalar(
            select(func.count(Booking.id)).where(
                Booking.schedule_slot_id == slot_id, Booking.status != BookingStatus.CANCELLED
            )
        ) or 0

    def find_active(self, client_id: int, slot_id: int) -> Booking | None:
        return self.db.scalar(
            select(Booking).where(
                Booking.client_id == client_id,
                Booking.schedule_slot_id == slot_id,
                Booking.status != BookingStatus.CANCELLED,
            )
        )

    def list_by_client(self, client_id: int) -> list[Booking]:
        return list(
            self.db.scalars(
                select(Booking).where(Booking.client_id == client_id).order_by(Booking.created_at.desc(), Booking.id.desc())
            )
        )

    def list_by_slot(self, slot_id: int) -> list[Booking]:
        return list(self.db.scalars(select(Booking).where(Booking.schedule_slot_id == slot_id)))

    def add(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.flush()
        return booking
