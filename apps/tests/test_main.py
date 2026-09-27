from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_ticket():
    payload = {
        "customer_id": 1,
        "subject": "I was charged twice for order ORD-1042",
        "description": "My card shows two successful payments for the same order.",
    }

    response = client.post("/tickets", json=payload)

    assert response.status_code == 201

    body = response.json()
    assert body["id"] >= 1
    assert body["customer_id"] == payload["customer_id"]
    assert body["subject"] == payload["subject"]
    assert body["status"] == "OPEN"
    assert "created_at" in body


def test_create_ticket_rejects_invalid_input():
    payload = {
        "customer_id": 0,
        "subject": "Bad",
        "description": "short",
    }

    response = client.post("/tickets", json=payload)

    assert response.status_code == 422


def test_get_missing_ticket_returns_404():
    response = client.get("/tickets/999999")

    assert response.status_code == 404