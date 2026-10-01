from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ResourceNotFoundError
from app.models import Role, ScheduleSlot, User
from app.repositories.hall_repository import HallRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.schedule import SlotCreate, SlotResponse
from app.services.audit_service import AuditService


def to_response(slot: ScheduleSlot, booked: int) -> SlotResponse:
    return SlotResponse(
        id=slot.id,
        title=slot.title,
        trainer_id=slot.trainer_id,
        trainer_name=slot.trainer.full_name,
        hall_id=slot.hall_id,
        hall_name=slot.hall.name,
        start_time=slot.start_time,
        end_time=slot.end_time,
        max_clients=slot.max_clients,
        booked=booked,
        free_places=max(slot.max_clients - booked, 0),
        price=slot.price,
    )


class ScheduleService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ScheduleRepository(db)
        self.halls = HallRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    def search(self, date_from: datetime | None, date_to: datetime | None, trainer_id: int | None,
               hall_id: int | None, limit: int = 100, offset: int = 0) -> list[SlotResponse]:
        slots = self.repo.search(date_from, date_to, trainer_id, hall_id, limit, offset)
        counts = self.repo.booked_counts([s.id for s in slots])
        return [to_response(s, counts.get(s.id, 0)) for s in slots]

    def get(self, slot_id: int) -> SlotResponse:
        slot = self.repo.get(slot_id)
        if slot is None:
            raise ResourceNotFoundError("Занятие не найдено")
        return to_response(slot, self.repo.booked_counts([slot.id]).get(slot.id, 0))

    def for_trainer(self, trainer: User) -> list[SlotResponse]:
        slots = self.repo.list_by_trainer(trainer.id)
        counts = self.repo.booked_counts([s.id for s in slots])
        return [to_response(s, counts.get(s.id, 0)) for s in slots]

    def create(self, data: SlotCreate, actor: User) -> SlotResponse:
        trainer = self.users.get(data.trainer_id)
        if trainer is None or trainer.role != Role.TRAINER:
            raise ResourceNotFoundError("Тренер не найден")
        hall = self.halls.get(data.hall_id)
        if hall is None:
            raise ResourceNotFoundError("Зал не найден")
        if data.max_clients > hall.capacity:
            raise ConflictError(f"Вместимость зала — {hall.capacity}, нельзя записать {data.max_clients}")

        for other in self.repo.overlapping(hall_id=data.hall_id, trainer_id=data.trainer_id,
                                           start=data.start_time, end=data.end_time):
            if other.hall_id == data.hall_id:
                raise ConflictError("Зал занят в это время")
            raise ConflictError("Тренер занят в это время")

        slot = self.repo.add(ScheduleSlot(**data.model_dump()))
        self.audit.log("SLOT_CREATED", f"Создано занятие '{slot.title}' #{slot.id}", actor.id)
        self.db.commit()
        self.db.refresh(slot)
        return to_response(slot, 0)
