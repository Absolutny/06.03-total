from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, ScheduleSlot


class ScheduleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, slot_id: int, lock: bool = False) -> ScheduleSlot | None:
        """lock=True — SELECT ... FOR UPDATE (PostgreSQL): защита от гонки при записи на последнее место."""
        stmt = select(ScheduleSlot).where(ScheduleSlot.id == slot_id)
        if lock:
            stmt = stmt.with_for_update(of=ScheduleSlot)
        return self.db.scalar(stmt)

    def search(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        trainer_id: int | None = None,
        hall_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ScheduleSlot]:
        stmt = select(ScheduleSlot).order_by(ScheduleSlot.start_time)
        if date_from:
            stmt = stmt.where(ScheduleSlot.start_time >= date_from)
        if date_to:
            stmt = stmt.where(ScheduleSlot.start_time <= date_to)
        if trainer_id:
            stmt = stmt.where(ScheduleSlot.trainer_id == trainer_id)
        if hall_id:
            stmt = stmt.where(ScheduleSlot.hall_id == hall_id)
        return list(self.db.scalars(stmt.limit(limit).offset(offset)))

    def list_by_trainer(self, trainer_id: int) -> list[ScheduleSlot]:
        stmt = select(ScheduleSlot).where(ScheduleSlot.trainer_id == trainer_id).order_by(ScheduleSlot.start_time)
        return list(self.db.scalars(stmt))

    def overlapping(self, *, hall_id: int | None, trainer_id: int | None, start: datetime, end: datetime):
        """Слоты, пересекающиеся по времени в том же зале или у того же тренера."""
        stmt = select(ScheduleSlot).where(ScheduleSlot.start_time < end, ScheduleSlot.end_time > start)
        conditions = []
        if hall_id:
            conditions.append(ScheduleSlot.hall_id == hall_id)
        if trainer_id:
            conditions.append(ScheduleSlot.trainer_id == trainer_id)
        if conditions:
            stmt = stmt.where(conditions[0] if len(conditions) == 1 else conditions[0] | conditions[1])
        return list(self.db.scalars(stmt))

    def booked_counts(self, slot_ids: list[int]) -> dict[int, int]:
        if not slot_ids:
            return {}
        rows = self.db.execute(
            select(Booking.schedule_slot_id, func.count(Booking.id))
            .where(Booking.schedule_slot_id.in_(slot_ids), Booking.status != BookingStatus.CANCELLED)
            .group_by(Booking.schedule_slot_id)
        ).all()
        return {slot_id: count for slot_id, count in rows}

    def add(self, slot: ScheduleSlot) -> ScheduleSlot:
        self.db.add(slot)
        self.db.flush()
        return slot
