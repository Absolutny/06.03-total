from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NoActiveSubscriptionError,
    PermissionDeniedError,
    ResourceNotFoundError,
    SlotIsFullError,
)
from app.models import Booking, BookingStatus, Role, User
from app.repositories.booking_repository import BookingRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.audit_service import AuditService


class BookingService:
    def __init__(self, db: Session, bookings: BookingRepository | None = None,
                 schedule: ScheduleRepository | None = None,
                 subscriptions: SubscriptionRepository | None = None,
                 audit: AuditService | None = None):
        self.db = db
        self.bookings = bookings or BookingRepository(db)
        self.schedule = schedule or ScheduleRepository(db)
        self.subscriptions = subscriptions or SubscriptionRepository(db)
        self.audit = audit or AuditService(db)

    def create_booking(self, client_id: int, slot_id: int) -> Booking:
        # lock=True: блокировка строки занятия до конца транзакции (PostgreSQL) — нет гонки за последнее место
        slot = self.schedule.get(slot_id, lock=True)
        if slot is None:
            raise ResourceNotFoundError("Занятие не найдено")
        if slot.start_time <= datetime.now():
            raise ConflictError("Запись на прошедшее или начавшееся занятие невозможна")
        if self.bookings.find_active(client_id, slot_id):
            raise ConflictError("Вы уже записаны на это занятие")
        if self.bookings.count_by_schedule_slot_id(slot_id) >= slot.max_clients:
            raise SlotIsFullError("Свободных мест на занятие нет")

        subscription = self.subscriptions.find_usable(client_id, slot.start_time.date())
        if subscription is None:
            raise NoActiveSubscriptionError("Нет действующего абонемента на дату занятия")
        if subscription.visits_left is not None:
            subscription.visits_left -= 1

        booking = self.bookings.add(
            Booking(client_id=client_id, schedule_slot_id=slot_id, subscription_id=subscription.id,
                    status=BookingStatus.BOOKED)
        )
        self.audit.log("BOOKING_CREATED", f"Запись #{booking.id} на занятие #{slot_id}", client_id)
        self.db.commit()
        return booking

    def cancel_booking(self, actor: User, booking_id: int) -> None:
        booking = self.bookings.get(booking_id)
        is_staff = actor.role in (Role.ADMIN, Role.MANAGER)
        # Чужую запись не раскрываем: для клиента она «не существует»
        if booking is None or (booking.client_id != actor.id and not is_staff):
            raise ResourceNotFoundError("Запись не найдена")
        if booking.status != BookingStatus.BOOKED:
            raise ConflictError("Отменить можно только активную запись")
        if booking.slot.start_time <= datetime.now() and not is_staff:
            raise ConflictError("Занятие уже началось, отмена невозможна")

        booking.status = BookingStatus.CANCELLED
        if booking.subscription_id:
            # возвращаем визит на абонемент
            sub = self.subscriptions.get(booking.subscription_id)
            if sub is not None and sub.visits_left is not None:
                sub.visits_left += 1
        self.audit.log("BOOKING_CANCELLED", f"Отменена запись #{booking.id}", actor.id)
        self.db.commit()

    def my_bookings(self, client_id: int) -> list[Booking]:
        return self.bookings.list_by_client(client_id)

    def mark_attendance(self, actor: User, booking_id: int, attended: bool) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise ResourceNotFoundError("Запись не найдена")
        if actor.role != Role.ADMIN and booking.slot.trainer_id != actor.id:
            raise PermissionDeniedError("Можно отмечать посещаемость только на своих занятиях")
        if booking.status == BookingStatus.CANCELLED:
            raise ConflictError("Запись отменена")
        booking.status = BookingStatus.ATTENDED if attended else BookingStatus.BOOKED
        self.audit.log("ATTENDANCE_MARKED", f"Запись #{booking.id}: {booking.status}", actor.id)
        self.db.commit()
        return booking

    def slot_bookings(self, actor: User, slot_id: int) -> list[Booking]:
        slot = self.schedule.get(slot_id)
        if slot is None:
            raise ResourceNotFoundError("Занятие не найдено")
        if actor.role != Role.ADMIN and slot.trainer_id != actor.id:
            raise PermissionDeniedError("Это не ваше занятие")
        return self.bookings.list_by_slot(slot_id)
