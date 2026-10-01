"""Unit-тесты BookingService: репозитории замоканы, БД не нужна."""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    ConflictError, NoActiveSubscriptionError, ResourceNotFoundError, SlotIsFullError,
)
from app.models import ScheduleSlot, Subscription
from app.services.booking_service import BookingService


@pytest.fixture
def deps():
    return {
        "db": MagicMock(), "bookings": MagicMock(), "schedule": MagicMock(),
        "subscriptions": MagicMock(), "audit": MagicMock(),
    }


@pytest.fixture
def service(deps):
    return BookingService(**deps)


def _slot(max_clients=10, hours_ahead=24) -> ScheduleSlot:
    return ScheduleSlot(id=1, max_clients=max_clients, start_time=datetime.now() + timedelta(hours=hours_ahead))


def test_create_booking_raises_when_slot_is_full(service, deps):
    deps["schedule"].get.return_value = _slot(max_clients=10)
    deps["bookings"].find_active.return_value = None
    deps["bookings"].count_by_schedule_slot_id.return_value = 10

    with pytest.raises(SlotIsFullError):
        service.create_booking(1, 1)
    deps["db"].commit.assert_not_called()


def test_create_booking_raises_when_slot_missing(service, deps):
    deps["schedule"].get.return_value = None
    with pytest.raises(ResourceNotFoundError):
        service.create_booking(1, 99)


def test_create_booking_rejects_past_slot(service, deps):
    deps["schedule"].get.return_value = _slot(hours_ahead=-1)
    with pytest.raises(ConflictError):
        service.create_booking(1, 1)


def test_create_booking_rejects_duplicate(service, deps):
    deps["schedule"].get.return_value = _slot()
    deps["bookings"].find_active.return_value = object()
    with pytest.raises(ConflictError):
        service.create_booking(1, 1)


def test_create_booking_requires_active_subscription(service, deps):
    deps["schedule"].get.return_value = _slot()
    deps["bookings"].find_active.return_value = None
    deps["bookings"].count_by_schedule_slot_id.return_value = 0
    deps["subscriptions"].find_usable.return_value = None
    with pytest.raises(NoActiveSubscriptionError):
        service.create_booking(1, 1)


def test_create_booking_decrements_visits_and_commits(service, deps):
    sub = Subscription(id=7, visits_left=3, start_date=date.today(), end_date=date.today() + timedelta(days=5))
    deps["schedule"].get.return_value = _slot()
    deps["bookings"].find_active.return_value = None
    deps["bookings"].count_by_schedule_slot_id.return_value = 0
    deps["subscriptions"].find_usable.return_value = sub
    deps["bookings"].add.side_effect = lambda b: b

    booking = service.create_booking(5, 1)

    assert sub.visits_left == 2
    assert booking.subscription_id == 7 and booking.client_id == 5
    deps["db"].commit.assert_called_once()


def test_unlimited_subscription_visits_not_decremented(service, deps):
    sub = Subscription(id=8, visits_left=None, start_date=date.today(), end_date=date.today() + timedelta(days=5))
    deps["schedule"].get.return_value = _slot()
    deps["bookings"].find_active.return_value = None
    deps["bookings"].count_by_schedule_slot_id.return_value = 0
    deps["subscriptions"].find_usable.return_value = sub
    deps["bookings"].add.side_effect = lambda b: b

    service.create_booking(5, 1)
    assert sub.visits_left is None
