from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import schedule_service
from app.models import User
from app.schemas.schedule import SlotCreate, SlotResponse
from app.security.dependencies import get_current_user, require_staff
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/api/v1/schedule", tags=["Schedule"])


def _naive(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=None) if value else None


@router.get("", response_model=list[SlotResponse], summary="Расписание с фильтрами по датам, тренеру, залу")
def get_schedule(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    trainer_id: int | None = Query(default=None, gt=0),
    hall_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    service: ScheduleService = Depends(schedule_service),
):
    return service.search(_naive(date_from), _naive(date_to), trainer_id, hall_id, limit, offset)


@router.get("/{slot_id}", response_model=SlotResponse, summary="Занятие по id")
def get_slot(slot_id: int, _: User = Depends(get_current_user), service: ScheduleService = Depends(schedule_service)):
    return service.get(slot_id)


@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED,
             summary="Создать занятие (ADMIN/MANAGER)")
def create_slot(data: SlotCreate, actor: User = Depends(require_staff),
                service: ScheduleService = Depends(schedule_service)):
    return service.create(data, actor)
