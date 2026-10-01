"""Интеграционные тесты: RBAC, расписание, бронирование, абонементы, отчёты."""
from datetime import date, timedelta

import pytest

from tests.conftest import me


# ---------- RBAC ----------
def test_client_cannot_create_slot_or_hall(client, headers):
    assert client.post("/api/v1/halls", headers=headers["client"], json={"name": "Зал X", "capacity": 5}).status_code == 403
    assert client.post("/api/v1/schedule", headers=headers["client"], json={}).status_code in (403, 422)


def test_admin_endpoints_forbidden_for_non_admin(client, headers):
    for role in ("client", "trainer", "manager"):
        assert client.get("/api/v1/admin/audit-logs", headers=headers[role]).status_code == 403
    assert client.get("/api/v1/admin/audit-logs", headers=headers["admin"]).status_code == 200


def test_only_admin_can_hire_staff(client, headers):
    payload = {"email": "newtrainer@complex.com", "password": "Tr41ner!Pass", "full_name": "Новый Тренер", "role": "TRAINER"}
    assert client.post("/api/v1/admin/staff", headers=headers["manager"], json=payload).status_code == 403
    r = client.post("/api/v1/admin/staff", headers=headers["admin"], json=payload)
    assert r.status_code in (201, 409) and (r.status_code == 409 or r.json()["role"] == "TRAINER")


def test_staff_creation_cannot_create_client_role(client, headers):
    payload = {"email": "x@complex.com", "password": "Tr41ner!Pass", "full_name": "Иван Иванов", "role": "CLIENT"}
    assert client.post("/api/v1/admin/staff", headers=headers["admin"], json=payload).status_code == 422


# ---------- Расписание ----------
def test_schedule_filters_and_free_places(client, headers, make_slot):
    slot = make_slot(max_clients=7)
    assert slot["free_places"] == 7 and slot["booked"] == 0
    r = client.get("/api/v1/schedule", headers=headers["client"], params={"trainer_id": slot["trainer_id"], "hall_id": slot["hall_id"]})
    assert r.status_code == 200 and any(s["id"] == slot["id"] for s in r.json())
    assert client.get("/api/v1/schedule", headers=headers["client"], params={"trainer_id": 999999}).json() == []


def test_overlapping_slot_rejected(client, headers, make_slot):
    slot = make_slot()
    r = client.post("/api/v1/schedule", headers=headers["manager"], json={
        "title": "Пересечение", "trainer_id": slot["trainer_id"], "hall_id": slot["hall_id"],
        "start_time": slot["start_time"], "end_time": slot["end_time"], "max_clients": 3})
    assert r.status_code == 409


def test_slot_capacity_cannot_exceed_hall(client, headers):
    hall = client.get("/api/v1/halls", headers=headers["manager"]).json()[0]
    trainer_id = me(client, headers["trainer"])["id"]
    r = client.post("/api/v1/schedule", headers=headers["manager"], json={
        "title": "Слишком много", "trainer_id": trainer_id, "hall_id": hall["id"],
        "start_time": "2031-01-01T10:00:00", "end_time": "2031-01-01T11:00:00", "max_clients": hall["capacity"] + 1})
    assert r.status_code == 409


def test_invalid_time_range_returns_422(client, headers):
    r = client.post("/api/v1/schedule", headers=headers["manager"], json={
        "title": "Ошибка", "trainer_id": 1, "hall_id": 1,
        "start_time": "2031-01-01T11:00:00", "end_time": "2031-01-01T10:00:00", "max_clients": 3})
    assert r.status_code == 422


# ---------- Бронирование ----------
def test_booking_lifecycle(client, make_slot, new_client_user):
    h, _user = new_client_user
    slot = make_slot(max_clients=3)

    created = client.post("/api/v1/bookings", headers=h, json={"schedule_slot_id": slot["id"]})
    assert created.status_code == 201 and created.json()["status"] == "BOOKED"
    booking_id = created.json()["id"]

    assert client.post("/api/v1/bookings", headers=h, json={"schedule_slot_id": slot["id"]}).status_code == 409  # дубль
    assert [b["id"] for b in client.get("/api/v1/bookings/my", headers=h).json()] == [booking_id]
    assert client.get(f"/api/v1/schedule/{slot['id']}", headers=h).json()["booked"] == 1

    assert client.delete(f"/api/v1/bookings/{booking_id}", headers=h).status_code == 204
    assert client.get(f"/api/v1/schedule/{slot['id']}", headers=h).json()["booked"] == 0
    assert client.delete(f"/api/v1/bookings/{booking_id}", headers=h).status_code == 409  # уже отменена


def test_full_slot_returns_409_slot_is_full(client, make_slot, make_client):
    first, _ = make_client()
    second, _ = make_client()
    slot = make_slot(max_clients=1)
    assert client.post("/api/v1/bookings", headers=first, json={"schedule_slot_id": slot["id"]}).status_code == 201
    r = client.post("/api/v1/bookings", headers=second, json={"schedule_slot_id": slot["id"]})
    assert r.status_code == 409 and r.json()["code"] == "slot_is_full"


def test_booking_without_subscription_returns_402(client, make_slot, make_client):
    h, _ = make_client(sub_type=None)
    slot = make_slot()
    r = client.post("/api/v1/bookings", headers=h, json={"schedule_slot_id": slot["id"]})
    assert r.status_code == 402 and r.json()["code"] == "no_active_subscription"


def test_only_clients_can_book(client, headers, make_slot):
    slot = make_slot()
    for role in ("admin", "manager", "trainer"):
        assert client.post("/api/v1/bookings", headers=headers[role], json={"schedule_slot_id": slot["id"]}).status_code == 403


def test_cannot_cancel_foreign_booking_idor(client, headers, make_slot, new_client_user):
    owner, _ = new_client_user
    slot = make_slot()
    booking_id = client.post("/api/v1/bookings", headers=owner, json={"schedule_slot_id": slot["id"]}).json()["id"]
    # другой клиент (демо) пытается отменить чужую запись → 404, а не 403 (существование не раскрываем)
    assert client.delete(f"/api/v1/bookings/{booking_id}", headers=headers["client"]).status_code == 404
    # менеджер — может
    assert client.delete(f"/api/v1/bookings/{booking_id}", headers=headers["manager"]).status_code == 204


def test_single_visit_subscription_is_consumed_and_restored(client, make_slot, make_client):
    h, _ = make_client(sub_type="SINGLE")
    first, second = make_slot(), make_slot()

    booking = client.post("/api/v1/bookings", headers=h, json={"schedule_slot_id": first["id"]})
    assert booking.status_code == 201
    assert client.get("/api/v1/subscriptions/my", headers=h).json()[0]["visits_left"] == 0
    assert client.post("/api/v1/bookings", headers=h, json={"schedule_slot_id": second["id"]}).status_code == 402

    client.delete(f"/api/v1/bookings/{booking.json()['id']}", headers=h)
    assert client.get("/api/v1/subscriptions/my", headers=h).json()[0]["visits_left"] == 1


# ---------- Тренер ----------
def test_trainer_marks_attendance_only_on_own_slots(client, headers, make_slot, new_client_user):
    h, _ = new_client_user
    slot = make_slot()
    booking_id = client.post("/api/v1/bookings", headers=h, json={"schedule_slot_id": slot["id"]}).json()["id"]

    r = client.post(f"/api/v1/trainer/bookings/{booking_id}/attendance", headers=headers["trainer"], json={"attended": True})
    assert r.status_code == 200 and r.json()["status"] == "ATTENDED"
    assert client.get("/api/v1/trainer/schedule", headers=headers["trainer"]).status_code == 200
    # клиент не имеет доступа к панели тренера
    assert client.get("/api/v1/trainer/schedule", headers=headers["client"]).status_code == 403


# ---------- Абонементы и отчёты ----------
def test_issue_subscription_and_revenue_report(client, headers):
    today = date.today()
    uid = me(client, headers["client"])["id"]
    before = client.get("/api/v1/admin/reports/revenue", headers=headers["admin"],
                        params={"date_from": today.isoformat(), "date_to": today.isoformat()}).json()
    r = client.post("/api/v1/subscriptions/issue", headers=headers["manager"],
                    json={"client_id": uid, "type": "UNLIMITED", "duration_days": 30, "amount": "2500.50"})
    assert r.status_code == 201 and r.json()["is_active"] is True
    after = client.get("/api/v1/admin/reports/revenue", headers=headers["admin"],
                       params={"date_from": today.isoformat(), "date_to": (today + timedelta(days=1)).isoformat()}).json()
    assert after["payments_count"] == before["payments_count"] + 1
    assert float(after["total_revenue"]) - float(before["total_revenue"]) == pytest.approx(2500.50)


def test_issue_subscription_to_unknown_client_returns_404(client, headers):
    r = client.post("/api/v1/subscriptions/issue", headers=headers["manager"],
                    json={"client_id": 999999, "type": "MONTHLY", "amount": "100"})
    assert r.status_code == 404


def test_audit_log_records_events(client, headers):
    items = client.get("/api/v1/admin/audit-logs", headers=headers["admin"], params={"per_page": 200}).json()["items"]
    assert {"LOGIN_SUCCESS"} <= {i["event_type"] for i in items}


def test_error_responses_have_unified_format(client, headers):
    r = client.get("/api/v1/schedule/999999", headers=headers["client"])
    assert r.status_code == 404
    assert set(r.json()) >= {"status", "code", "message", "timestamp"}
