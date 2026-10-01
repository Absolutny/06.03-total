from fastapi import APIRouter, Depends

from app.api.deps import booking_service, schedule_service
from app.models import User
from app.schemas.booking import AttendanceRequest, BookingResponse
from app.schemas.schedule import SlotResponse
from app.security.dependencies import require_trainer
from app.services.booking_service import BookingService
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/api/v1/trainer", tags=["Trainer"])


@router.get("/schedule", response_model=list[SlotResponse], summary="Мои занятия")
def my_schedule(trainer: User = Depends(require_trainer), service: ScheduleService = Depends(schedule_service)):
    return service.for_trainer(trainer)


@router.get("/slots/{slot_id}/bookings", response_model=list[BookingResponse], summary="Записи на моё занятие")
def slot_bookings(slot_id: int, trainer: User = Depends(require_trainer),
                  service: BookingService = Depends(booking_service)):
    return service.slot_bookings(trainer, slot_id)


@router.post("/bookings/{booking_id}/attendance", response_model=BookingResponse,
             summary="Отметить посещаемость")
def mark_attendance(booking_id: int, data: AttendanceRequest, trainer: User = Depends(require_trainer),
                    service: BookingService = Depends(booking_service)):
    return service.mark_attendance(trainer, booking_id, data.attended)
