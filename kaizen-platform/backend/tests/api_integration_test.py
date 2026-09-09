import os
from pathlib import Path
from uuid import uuid4

import pytest


pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

TEST_DATABASE = Path(__file__).with_name("kaizen_test.db")
os.environ["KAIZEN_ENVIRONMENT"] = "test"
os.environ["KAIZEN_DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DATABASE}"
os.environ["KAIZEN_AUTO_CREATE_TABLES"] = "true"
os.environ["KAIZEN_DEBUG"] = "true"

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    TEST_DATABASE.unlink(missing_ok=True)
    with TestClient(app) as test_client:
        yield test_client
    TEST_DATABASE.unlink(missing_ok=True)


def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Miranda",
            "email": "miranda@example.com",
            "password": "Kaizen#Seguro2026",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_productivity_crud_and_notification_status(client: TestClient) -> None:
    headers = auth_headers(client)

    habit = client.post(
        "/api/v1/habits",
        headers=headers,
        json={
            "name": "Estudar Python",
            "category": "Estudos",
            "reminder_time": "19:00:00",
            "scheduled_days": [True, True, True, True, True, False, False],
        },
    )
    assert habit.status_code == 201, habit.text
    habit_id = habit.json()["id"]

    completion = client.put(
        f"/api/v1/habits/{habit_id}/completions/2026-08-31",
        headers=headers,
    )
    assert completion.status_code == 200, completion.text
    assert "2026-08-31" in completion.json()["completed_dates"]

    task = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Conectar o frontend",
            "due_at": "2026-09-01T22:00:00Z",
            "estimated_minutes": 90,
        },
    )
    assert task.status_code == 201, task.text
    task_data = task.json()

    updated = client.patch(
        f"/api/v1/tasks/{task_data['id']}",
        headers=headers,
        json={"expected_version": task_data["version"], "status": "doing"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "doing"

    notification_status = client.get("/api/v1/notifications/status", headers=headers)
    assert notification_status.status_code == 200, notification_status.text
    assert notification_status.json()["devices"] == []

    deleted = client.delete(
        f"/api/v1/tasks/{task_data['id']}?version={updated.json()['version']}",
        headers=headers,
    )
    assert deleted.status_code == 204, deleted.text

    sync = client.get("/api/v1/sync/pull", headers=headers)
    assert sync.status_code == 200, sync.text
    assert any(item["deleted_at"] for item in sync.json()["tasks"])


def test_client_id_makes_offline_create_idempotent(client: TestClient) -> None:
    headers = auth_headers(client)
    task_id = str(uuid4())
    payload = {"id": task_id, "title": "Criada sem internet", "status": "todo"}

    first = client.post("/api/v1/tasks", headers=headers, json=payload)
    repeated = client.post("/api/v1/tasks", headers=headers, json=payload)

    assert first.status_code == 201, first.text
    assert repeated.status_code == 201, repeated.text
    assert first.json()["id"] == task_id
    assert repeated.json()["id"] == task_id


def test_google_oauth_reports_missing_configuration(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/google/start",
        params={"return_to": "http://localhost:5500/Kaizen-Life-Foco.html"},
    )
    assert response.status_code == 503, response.text


def test_notification_cron_is_hidden_when_disabled(client: TestClient) -> None:
    response = client.post("/api/v1/internal/notifications/dispatch")
    assert response.status_code == 404, response.text


def test_notification_cron_requires_its_own_secret(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cron_secret = "segredo-do-agendador-com-mais-de-trinta-e-dois-caracteres"
    monkeypatch.setattr(settings, "notification_cron_enabled", True)
    monkeypatch.setattr(settings, "cron_secret", cron_secret)

    unauthorized = client.post("/api/v1/internal/notifications/dispatch")
    assert unauthorized.status_code == 401, unauthorized.text

    dispatched = client.post(
        "/api/v1/internal/notifications/dispatch",
        headers={"X-Kaizen-Cron-Secret": cron_secret},
    )
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json() == {"status": "ok", "sent_devices": 0}
