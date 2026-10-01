from fastapi import APIRouter, Depends, status

from app.api.deps import booking_service
from app.models import Role, User
from app.schemas.booking import BookingCreate, BookingResponse
from app.security.dependencies import get_current_user, require_client
from app.services.booking_service import BookingService

router = APIRouter(prefix="/api/v1/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED,
             summary="Записаться на занятие (CLIENT)")
def create_booking(data: BookingCreate, client: User = Depends(require_client),
                   service: BookingService = Depends(booking_service)):
    return service.create_booking(client.id, data.schedule_slot_id)


# ВАЖНО: /my объявлен раньше /{booking_id}, чтобы путь не перехватывался параметром
@router.get("/my", response_model=list[BookingResponse], summary="История моих записей")
def my_bookings(user: User = Depends(get_current_user), service: BookingService = Depends(booking_service)):
    return service.my_bookings(user.id)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Отменить запись (владелец или ADMIN/MANAGER)")
def cancel_booking(booking_id: int, user: User = Depends(get_current_user),
                   service: BookingService = Depends(booking_service)):
    service.cancel_booking(user, booking_id)
