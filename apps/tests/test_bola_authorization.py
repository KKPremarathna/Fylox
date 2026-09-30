"""
BOLA (Broken Object Level Authorization) regression tests.

A customer must never be able to read or modify another customer's ticket by
guessing or iterating ticket IDs.

Fixtures used
─────────────
customer_client        – TestClient authenticated as the ticket owner (customer_user).
second_customer_client – TestClient authenticated as a different customer
                         (second_customer_user) who does NOT own customer_ticket.
admin_client           – TestClient authenticated as an ADMIN.
customer_ticket        – A Ticket owned by customer_user.
db_session             – Direct SQLAlchemy session for post-request DB assertions.

All fixtures are function-scoped; the base `client` fixture is the sole
place that clears app.dependency_overrides so overrides do not bleed
between tests.
"""

import pytest

from backend.messages.models import TicketMessage

# ── Shared request payloads ───────────────────────────────────────────────────

_MESSAGE_BODY = {"content": "Hello, I need an update on my billing issue."}
_CATEGORY_REVIEW_BODY = {"final_category": "OTHER"}
_ADMIN_UPDATE_BODY = {"status": "IN_PROGRESS"}
_NONEXISTENT_ID = 999_999


# ═════════════════════════════════════════════════════════════════════════════
# 1. GET /tickets/{ticket_id}
# ═════════════════════════════════════════════════════════════════════════════


def test_get_ticket_owner_200(customer_client, customer_ticket):
    """Ticket owner can read their own ticket."""
    resp = customer_client.get(f"/tickets/{customer_ticket.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == customer_ticket.id


def test_get_ticket_non_owner_403_no_data_leak(second_customer_client, customer_ticket):
    """Different customer is blocked and the response body exposes no ticket data."""
    resp = second_customer_client.get(f"/tickets/{customer_ticket.id}")
    assert resp.status_code == 403

    body = resp.text
    assert customer_ticket.subject not in body, (
        "403 response must not contain the ticket subject"
    )
    assert customer_ticket.description not in body, (
        "403 response must not contain the ticket description"
    )


def test_get_ticket_admin_200(admin_client, customer_ticket):
    """Admin can read any ticket regardless of ownership."""
    resp = admin_client.get(f"/tickets/{customer_ticket.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == customer_ticket.id


def test_get_ticket_nonexistent_404(customer_client):
    """Any authenticated user receives 404 for a ticket that does not exist."""
    resp = customer_client.get(f"/tickets/{_NONEXISTENT_ID}")
    assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 2. GET /tickets/{ticket_id}/messages
# ═════════════════════════════════════════════════════════════════════════════


def test_get_messages_owner_200(customer_client, customer_ticket):
    """Ticket owner can list messages for their own ticket."""
    resp = customer_client.get(f"/tickets/{customer_ticket.id}/messages")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_messages_non_owner_403_no_data_leak(
    second_customer_client, customer_ticket, db_session
):
    """Different customer is blocked and no message content is exposed."""
    # Seed a message with sensitive content so there is something to potentially leak.
    secret_content = "Confidential: card number ending in 4242."
    msg = TicketMessage(
        ticket_id=customer_ticket.id,
        sender_id=customer_ticket.customer_id,
        sender_type="CUSTOMER",
        content=secret_content,
    )
    db_session.add(msg)
    db_session.commit()

    resp = second_customer_client.get(f"/tickets/{customer_ticket.id}/messages")
    assert resp.status_code == 403
    assert secret_content not in resp.text, (
        "403 response must not contain message content"
    )


def test_get_messages_admin_200(admin_client, customer_ticket):
    """Admin can list messages for any ticket."""
    resp = admin_client.get(f"/tickets/{customer_ticket.id}/messages")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_messages_nonexistent_404(customer_client):
    """Any authenticated user receives 404 for messages on a nonexistent ticket."""
    resp = customer_client.get(f"/tickets/{_NONEXISTENT_ID}/messages")
    assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 3. POST /tickets/{ticket_id}/messages
# ═════════════════════════════════════════════════════════════════════════════


def test_create_message_owner_201(customer_client, customer_ticket):
    """Ticket owner can post a message to their own ticket."""
    resp = customer_client.post(
        f"/tickets/{customer_ticket.id}/messages",
        json=_MESSAGE_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticket_id"] == customer_ticket.id
    assert data["content"] == _MESSAGE_BODY["content"]
    assert data["sender_type"] == "CUSTOMER"


def test_create_message_non_owner_403_no_message_created(
    second_customer_client, customer_ticket, db_session
):
    """
    Different customer is blocked from posting and no message is persisted.
    The DB assertion confirms the 403 is not a soft failure that still writes.
    """
    resp = second_customer_client.post(
        f"/tickets/{customer_ticket.id}/messages",
        json=_MESSAGE_BODY,
    )
    assert resp.status_code == 403

    # Verify no message was written to the database.
    count = (
        db_session.query(TicketMessage)
        .filter_by(ticket_id=customer_ticket.id)
        .count()
    )
    assert count == 0, (
        "A rejected POST must not create a message record in the database"
    )


def test_create_message_admin_201(admin_client, customer_ticket):
    """Admin can post a message to any ticket."""
    resp = admin_client.post(
        f"/tickets/{customer_ticket.id}/messages",
        json=_MESSAGE_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticket_id"] == customer_ticket.id
    assert data["sender_type"] == "ADMIN"


def test_create_message_nonexistent_404(customer_client):
    """Posting a message to a nonexistent ticket returns 404."""
    resp = customer_client.post(
        f"/tickets/{_NONEXISTENT_ID}/messages",
        json=_MESSAGE_BODY,
    )
    assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 4. GET /tickets/{ticket_id}/activity
# ═════════════════════════════════════════════════════════════════════════════


def test_get_activity_owner_200(customer_client, customer_ticket):
    """Ticket owner can read activity for their own ticket."""
    resp = customer_client.get(f"/tickets/{customer_ticket.id}/activity")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_activity_non_owner_403(second_customer_client, customer_ticket):
    """Different customer cannot read ticket activity."""
    resp = second_customer_client.get(f"/tickets/{customer_ticket.id}/activity")
    assert resp.status_code == 403


def test_get_activity_admin_200(admin_client, customer_ticket):
    """Admin can read activity for any ticket."""
    resp = admin_client.get(f"/tickets/{customer_ticket.id}/activity")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_activity_nonexistent_404(customer_client):
    """Activity endpoint returns 404 for a nonexistent ticket."""
    resp = customer_client.get(f"/tickets/{_NONEXISTENT_ID}/activity")
    assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 5. AI category endpoints — must remain admin-only regardless of ownership
# ═════════════════════════════════════════════════════════════════════════════

_AI_ENDPOINTS = [
    pytest.param(
        "post",
        "ai/category-suggestion",
        None,
        id="suggest",
    ),
    pytest.param(
        "patch",
        "accept-ai-category",
        None,
        id="accept",
    ),
    pytest.param(
        "patch",
        "category-review",
        _CATEGORY_REVIEW_BODY,
        id="review",
    ),
]


@pytest.mark.parametrize("method,path_suffix,body", _AI_ENDPOINTS)
def test_ai_endpoints_ticket_owner_customer_gets_403(
    customer_client, customer_ticket, method, path_suffix, body
):
    """
    The ticket owner (a CUSTOMER) is forbidden from all three AI endpoints.
    Ownership of the ticket does not grant access to admin-only operations.
    """
    url = f"/tickets/{customer_ticket.id}/{path_suffix}"
    resp = getattr(customer_client, method)(url, json=body)
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path_suffix,body", _AI_ENDPOINTS)
def test_ai_endpoints_different_customer_gets_403(
    second_customer_client, customer_ticket, method, path_suffix, body
):
    """
    A customer who does not own the ticket is also forbidden from all three
    AI endpoints — neither ownership nor non-ownership matters; role alone gates access.
    """
    url = f"/tickets/{customer_ticket.id}/{path_suffix}"
    resp = getattr(second_customer_client, method)(url, json=body)
    assert resp.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# 6. PATCH /admin/tickets/{ticket_id}
# ═════════════════════════════════════════════════════════════════════════════


def test_admin_update_ticket_owner_customer_403_no_change(
    customer_client, customer_ticket, db_session
):
    """Ticket owner (customer) cannot call the admin update endpoint."""
    original_status = customer_ticket.status

    resp = customer_client.patch(
        f"/admin/tickets/{customer_ticket.id}",
        json=_ADMIN_UPDATE_BODY,
    )
    assert resp.status_code == 403

    # Confirm the ticket was not mutated.
    db_session.refresh(customer_ticket)
    assert customer_ticket.status == original_status, (
        "A rejected PATCH must not alter the ticket status in the database"
    )


def test_admin_update_ticket_different_customer_403_no_change(
    second_customer_client, customer_ticket, db_session
):
    """A non-owning customer also cannot call the admin update endpoint."""
    original_status = customer_ticket.status

    resp = second_customer_client.patch(
        f"/admin/tickets/{customer_ticket.id}",
        json=_ADMIN_UPDATE_BODY,
    )
    assert resp.status_code == 403

    db_session.refresh(customer_ticket)
    assert customer_ticket.status == original_status, (
        "A rejected PATCH must not alter the ticket status in the database"
    )


def test_admin_update_ticket_admin_200(admin_client, customer_ticket, db_session):
    """Admin can update any ticket's status via the admin endpoint."""
    resp = admin_client.patch(
        f"/admin/tickets/{customer_ticket.id}",
        json=_ADMIN_UPDATE_BODY,
    )
    assert resp.status_code == 200

    db_session.refresh(customer_ticket)
    assert customer_ticket.status == _ADMIN_UPDATE_BODY["status"], (
        "Admin update must persist the new status to the database"
    )
