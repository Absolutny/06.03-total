"""Общие фикстуры. Переменные окружения задаются ДО импорта приложения."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    JWT_SECRET="test-secret-key-that-is-at-least-32-bytes-long",
    ENVIRONMENT="test",
    BCRYPT_ROUNDS="4",
    SEED_DEMO_DATA="true",
    RATE_LIMIT_PER_MINUTE="100000",
    LOGIN_RATE_LIMIT_PER_MINUTE="100000",
)

import itertools  # noqa: E402
import uuid  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402

DEMO = {
    "admin": ("admin@complex.com", "Admin123!"),
    "manager": ("manager@complex.com", "Manager123!"),
    "trainer": ("trainer@complex.com", "Trainer123!"),
    "client": ("client@complex.com", "Client123!"),
}
STRONG_PASSWORD = "Str0ngPass1"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # запускает lifespan: create_all + seed
        yield c


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield


def login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def auth(client: TestClient, role: str) -> dict[str, str]:
    email, password = DEMO[role]
    return {"Authorization": f"Bearer {login(client, email, password)['access_token']}"}


def me(client: TestClient, headers: dict) -> dict:
    return client.get("/api/v1/auth/me", headers=headers).json()


@pytest.fixture
def headers(client):
    """Заголовки Authorization для демо-пользователей по ролям."""
    return {role: auth(client, role) for role in DEMO}


def create_client(client: TestClient, manager_headers: dict, sub_type: str | None = "MONTHLY"):
    """Регистрирует нового клиента; если sub_type задан — выдаёт абонемент. Возвращает (headers, user)."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": STRONG_PASSWORD, "full_name": "Тест Тестов"})
    assert r.status_code == 201, r.text
    user = r.json()
    h = {"Authorization": f"Bearer {login(client, email, STRONG_PASSWORD)['access_token']}"}
    if sub_type:
        issue = client.post("/api/v1/subscriptions/issue", headers=manager_headers,
                            json={"client_id": user["id"], "type": sub_type, "duration_days": 30, "amount": "1500.00"})
        assert issue.status_code == 201, issue.text
    return h, user


@pytest.fixture
def new_client_user(client, headers):
    """Свежий клиент с действующим месячным абонементом: (headers, user)."""
    return create_client(client, headers["manager"])


@pytest.fixture
def make_client(client, headers):
    """Фабрика клиентов: make_client(sub_type="SINGLE" | None | ...)."""
    return lambda sub_type="MONTHLY": create_client(client, headers["manager"], sub_type)


_counter = itertools.count()


@pytest.fixture
def make_slot(client, headers):
    """Фабрика занятий без пересечений по времени (в пределах срока абонемента)."""
    trainer_id = me(client, headers["trainer"])["id"]
    hall_id = client.get("/api/v1/halls", headers=headers["manager"]).json()[0]["id"]
    base = (datetime.now() + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)

    def _make(max_clients: int = 5, trainer: int | None = None, hall: int | None = None):
        start = base + timedelta(hours=2 * next(_counter) + 1, days=0)
        r = client.post("/api/v1/schedule", headers=headers["manager"], json={
            "title": "Тестовое занятие", "trainer_id": trainer or trainer_id, "hall_id": hall or hall_id,
            "start_time": start.isoformat(), "end_time": (start + timedelta(hours=1)).isoformat(),
            "max_clients": max_clients, "price": "300.00",
        })
        assert r.status_code == 201, r.text
        return r.json()

    return _make
