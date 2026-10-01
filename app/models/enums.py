from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    TRAINER = "TRAINER"
    CLIENT = "CLIENT"


class BookingStatus(StrEnum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    ATTENDED = "ATTENDED"


class SubscriptionType(StrEnum):
    MONTHLY = "MONTHLY"
    UNLIMITED = "UNLIMITED"
    SINGLE = "SINGLE"


class PaymentStatus(StrEnum):
    PAID = "PAID"
    REFUNDED = "REFUNDED"
