"""Интеграционные тесты: аутентификация, JWT, rate limit, заголовки."""
import uuid

from app.config import get_settings
from tests.conftest import DEMO, STRONG_PASSWORD, auth, login


def _email():
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def test_register_login_and_me(client):
    email = _email()
    r = client.post("/api/v1/auth/register", json={"email": email, "password": STRONG_PASSWORD, "full_name": "Иван Иванов"})
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "CLIENT" and "password" not in body and "password_hash" not in body

    tokens = login(client, email, STRONG_PASSWORD)
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == email


def test_register_cannot_choose_role(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": _email(), "password": STRONG_PASSWORD, "full_name": "Хакер Хакеров", "role": "ADMIN"})
    assert r.status_code == 201 and r.json()["role"] == "CLIENT"  # лишнее поле role игнорируется


def test_weak_password_returns_422_with_details(client):
    r = client.post("/api/v1/auth/register", json={"email": _email(), "password": "weakpass", "full_name": "Иван"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error" and "password" in body["details"]


def test_duplicate_email_returns_409(client):
    email = _email()
    payload = {"email": email, "password": STRONG_PASSWORD, "full_name": "Иван Иванов"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_errors_do_not_reveal_whether_account_exists(client):
    wrong_pw = client.post("/api/v1/auth/login", json={"email": DEMO["client"][0], "password": "Wrong123!"})
    unknown = client.post("/api/v1/auth/login", json={"email": _email(), "password": "Wrong123!"})
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json()["message"] == unknown.json()["message"]


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/v1/schedule").status_code == 401
    assert client.get("/api/v1/schedule", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotation_and_reuse_detection(client):
    tokens = login(client, *DEMO["client"])
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    new_tokens = first.json()

    # Старый refresh одноразовый: повторное использование отклоняется...
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401
    # ...и отзывает всю цепочку (возможная кража токена)
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert after.status_code == 401


def test_access_token_cannot_be_used_as_refresh(client):
    tokens = login(client, *DEMO["client"])
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


def test_change_password_revokes_refresh_tokens(client):
    email = _email()
    client.post("/api/v1/auth/register", json={"email": email, "password": STRONG_PASSWORD, "full_name": "Пётр Петров"})
    tokens = login(client, email, STRONG_PASSWORD)
    h = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = client.post("/api/v1/auth/change-password", headers=h,
                    json={"current_password": STRONG_PASSWORD, "new_password": "NewStr0ngPass2"})
    assert r.status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    login(client, email, "NewStr0ngPass2")


def test_login_rate_limit_returns_429(client):
    settings = get_settings()
    old = settings.login_rate_limit_per_minute
    settings.login_rate_limit_per_minute = 3
    try:
        codes = [client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "Wrong123!"}).status_code
                 for _ in range(5)]
    finally:
        settings.login_rate_limit_per_minute = old
    assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]


def test_security_headers_and_cors(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"

    allowed = client.options("/api/v1/auth/login", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    denied = client.options("/api/v1/auth/login", headers={
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in denied.headers


def test_swagger_and_openapi_available(client):
    assert client.get("/swagger-ui.html").status_code == 200
    spec = client.get("/v3/api-docs").json()
    assert "/api/v1/bookings" in spec["paths"] and "/api/v1/auth/login" in spec["paths"]


def test_sql_injection_payload_is_just_a_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@complex.com", "password": "' OR '1'='1"})
    assert r.status_code == 401
    assert auth(client, "admin")  # админ по-прежнему работает — таблицы целы
