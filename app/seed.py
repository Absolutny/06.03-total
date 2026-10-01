"""Первичное наполнение БД: администратор и (опционально) демо-данные."""
import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Hall, Role, ScheduleSlot, Subscription, SubscriptionType, User
from app.repositories.user_repository import UserRepository
from app.security.passwords import hash_password

logger = logging.getLogger(__name__)

DEMO_USERS = [
    ("admin@complex.com", "Admin123!", "Администратор Комплекса", Role.ADMIN),
    ("manager@complex.com", "Manager123!", "Менеджер Иванова", Role.MANAGER),
    ("trainer@complex.com", "Trainer123!", "Тренер Петров", Role.TRAINER),
    ("client@complex.com", "Client123!", "Клиент Сидоров", Role.CLIENT),
]


def seed(db: Session) -> None:
    settings = get_settings()
    users = UserRepository(db)

    if users.count() == 0 and not settings.seed_demo_data:
        password = settings.admin_password or "Aa1" + secrets.token_urlsafe(12)
        db.add(User(email=settings.admin_email.lower(), password_hash=hash_password(password),
                    full_name="Администратор Комплекса", role=Role.ADMIN))
        db.commit()
        if settings.admin_password:
            logger.info("Создан администратор %s (пароль из ADMIN_PASSWORD)", settings.admin_email)
        else:
            # Единственное место, где пароль выводится: показывается один раз при первом запуске
            logger.warning("Создан администратор %s, временный пароль: %s", settings.admin_email, password)

    if settings.seed_demo_data and users.count() == 0:
        logger.warning("SEED_DEMO_DATA=true: созданы тестовые аккаунты с публичными паролями. Не для production!")
        created = {}
        for email, password, name, role in DEMO_USERS:
            created[role] = users.add(User(email=email, password_hash=hash_password(password), full_name=name, role=role))
        hall = Hall(name="Тренажёрный зал", capacity=20)
        pool = Hall(name="Бассейн", capacity=12)
        db.add_all([hall, pool])
        db.flush()
        start = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        db.add_all([
            ScheduleSlot(title="Силовая тренировка", trainer_id=created[Role.TRAINER].id, hall_id=hall.id,
                         start_time=start, end_time=start + timedelta(hours=1), max_clients=10, price=400),
            ScheduleSlot(title="Аквааэробика", trainer_id=created[Role.TRAINER].id, hall_id=pool.id,
                         start_time=start + timedelta(hours=2), end_time=start + timedelta(hours=3), max_clients=8,
                         price=500),
        ])
        today = datetime.now().date()
        db.add(Subscription(client_id=created[Role.CLIENT].id, type=SubscriptionType.MONTHLY, visits_left=None,
                            start_date=today, end_date=today + timedelta(days=30), is_active=True))
        db.commit()
