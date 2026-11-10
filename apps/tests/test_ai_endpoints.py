import pytest
from sqlalchemy.exc import IntegrityError

from backend.ai import billing_analysis
from backend.ai import provider
from backend.ai.models import BillingAnalysisRecord
from backend.activity.models import TicketActivity
from backend.messages.models import TicketMessage
from backend.security import create_access_token


@pytest.fixture(autouse=True)
def block_live_gemini(monkeypatch):
    """
    No test in this module may make a live Gemini request.
    """
    def forbidden_call(*args, **kwargs):
        raise AssertionError(
            "Live Gemini calls are forbidden in endpoint tests."
        )

    monkeypatch.setattr(
        provider,
        "call_gemini_billing",
        forbidden_call,
    )

    monkeypatch.setattr(
        provider.settings,
        "billing_ai_provider",
        "deterministic",
    )


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        (
            "ai-reply",
            {"message": "Hello"},
        ),
        (
            "billing-analysis",
            {"order_id": 1},
        ),
    ],
)
def test_ai_endpoints_require_authentication(
    client,
    customer_ticket,
    endpoint,
    payload,
):
    response = client.post(
        f"/ai/tickets/{customer_ticket.id}/{endpoint}",
        json=payload,
    )

    assert response.status_code == 401


def test_customer_cannot_request_admin_billing_analysis(
    customer_client,
    customer_ticket,
    customer_order,
    db_session,
):
    response = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id},
    )

    assert response.status_code == 403
    assert db_session.query(BillingAnalysisRecord).count() == 0


def test_other_customer_cannot_generate_ticket_reply(
    second_customer_client,
    customer_ticket,
    db_session,
):
    response = second_customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json={"message": "Hello"},
    )

    assert response.status_code == 403
    assert db_session.query(TicketMessage).count() == 0
    assert db_session.query(TicketActivity).count() == 0


def test_admin_cannot_analyze_order_for_wrong_ticket_customer(
    admin_client,
    customer_ticket,
    second_customer_order,
    db_session,
):
    response = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": second_customer_order.id},
    )

    assert response.status_code == 400
    assert db_session.query(BillingAnalysisRecord).count() == 0


@pytest.mark.parametrize(
    ("provider_fails", "expected_reason"),
    [
        (False, "LIVE_PROVIDER_DISABLED"),
        (True, "PROVIDER_TIMEOUT"),
    ],
)
def test_billing_fallback_persists_record_and_activity(
    admin_client,
    admin_user,
    customer_ticket,
    customer_order,
    customer_payment,
    db_session,
    monkeypatch,
    provider_fails,
    expected_reason,
):
    if provider_fails:
        def fail_provider(*args, **kwargs):
            raise TimeoutError("Synthetic timeout")

        monkeypatch.setattr(
            billing_analysis,
            "execute_billing_analysis",
            fail_provider,
        )

    response = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/billing-analysis",
        json={"order_id": customer_order.id},
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["analysis_source"] == "FALLBACK"
    assert body["fallback_reason"] == expected_reason
    assert body["requires_human_review"] is True
    assert body["evidence_ids"] == [customer_payment.id]
    assert body["policy_source_ids"] == []

    # Reload through the test session rather than trusting JSON alone.
    db_session.expire_all()

    record = db_session.get(
        BillingAnalysisRecord,
        body["id"],
    )

    assert record is not None
    assert record.ticket_id == customer_ticket.id
    assert record.order_id == customer_order.id
    assert record.admin_id == admin_user.user_id
    assert record.requires_human_review is True
    assert record.analysis_source == "FALLBACK"
    assert record.fallback_reason == expected_reason
    assert record.evidence_ids == [customer_payment.id]

    activity = (
        db_session.query(TicketActivity)
        .filter(
            TicketActivity.ticket_id == customer_ticket.id,
            TicketActivity.event_type
            == "BILLING_ANALYSIS_GENERATED",
        )
        .one()
    )

    assert activity.actor_id == admin_user.user_id

    # Billing analysis stores a draft; it must not send it.
    assert db_session.query(TicketMessage).count() == 0


def test_order_reply_uses_authenticated_customers_order(
    customer_client,
    customer_ticket,
    customer_order,
    db_session,
):
    response = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json={
            "message": (
                f"Check order status for "
                f"order #{customer_order.order_number}"
            )
        },
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["action_taken"] == "REPLIED_VIA_ORDER_SUPPORT"
    assert customer_order.order_number in body["message_content"]
    assert customer_order.status in body["message_content"]

    messages = (
        db_session.query(TicketMessage)
        .filter(TicketMessage.ticket_id == customer_ticket.id)
        .order_by(TicketMessage.id.asc())
        .all()
    )

    # Customer message saved with customer authorship, AI reply saved with NULL sender_id
    assert len(messages) == 2
    assert messages[0].sender_type == "CUSTOMER"
    assert messages[0].sender_id == customer_ticket.customer_id
    assert customer_order.order_number in messages[0].content

    assert messages[1].sender_type == "AI"
    assert messages[1].sender_id is None
    assert messages[1].content == body["message_content"]


def test_admin_ai_reply_attributes_input_to_admin(
    admin_client,
    admin_user,
    customer_ticket,
    customer_order,
    db_session,
):
    response = admin_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json={
            "message": f"Check order status for order #{customer_order.order_number}"
        },
    )

    assert response.status_code == 200, response.text

    messages = (
        db_session.query(TicketMessage)
        .filter(TicketMessage.ticket_id == customer_ticket.id)
        .order_by(TicketMessage.id.asc())
        .all()
    )

    assert len(messages) == 2
    # Admin message MUST be attributed to admin, never to customer
    assert messages[0].sender_type == "ADMIN"
    assert messages[0].sender_id == admin_user.user_id
    assert messages[0].sender_id != customer_ticket.customer_id

    # AI message has sender_id NULL
    assert messages[1].sender_type == "AI"
    assert messages[1].sender_id is None


def test_no_reply_routing_retains_submitted_input_and_exposes_outcome(
    customer_client,
    customer_ticket,
    db_session,
):
    response = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json={"message": "I was charged twice, please refund my payment."},
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["action_taken"] == "ROUTED_WITHOUT_REPLY"
    assert body["message_content"] is None
    assert body["routing_decision"]["category"] == "BILLING_SUPPORT"

    messages = (
        db_session.query(TicketMessage)
        .filter(TicketMessage.ticket_id == customer_ticket.id)
        .all()
    )

    # Submitted customer input is retained in conversation
    assert len(messages) == 1
    assert messages[0].sender_type == "CUSTOMER"
    assert messages[0].sender_id == customer_ticket.customer_id
    assert "charged twice" in messages[0].content

    # Activities recorded: message creation and routing decision
    activities = (
        db_session.query(TicketActivity)
        .filter(TicketActivity.ticket_id == customer_ticket.id)
        .all()
    )
    event_types = {a.event_type for a in activities}
    assert "MESSAGE_CREATED" in event_types
    assert "AI_ROUTED" in event_types


def test_empty_or_whitespace_input_rejected_no_writes(
    customer_client,
    customer_ticket,
    db_session,
):
    for empty_input in ["", "   ", "\n\t"]:
        response = customer_client.post(
            f"/ai/tickets/{customer_ticket.id}/ai-reply",
            json={"message": empty_input},
        )
        assert response.status_code == 422
        assert "empty" in response.json()["detail"].lower()

    # Verify no writes occurred
    assert (
        db_session.query(TicketMessage)
        .filter(TicketMessage.ticket_id == customer_ticket.id)
        .count()
        == 0
    )
    assert (
        db_session.query(TicketActivity)
        .filter(TicketActivity.ticket_id == customer_ticket.id)
        .count()
        == 0
    )


def test_duplicate_submission_blocked_within_cooldown(
    customer_client,
    customer_ticket,
    customer_order,
    db_session,
):
    payload = {
        "message": f"Check order status for order #{customer_order.order_number}"
    }

    # First submission succeeds
    first_res = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json=payload,
    )
    assert first_res.status_code == 200

    # Rapid second submission with identical payload is rejected
    second_res = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json=payload,
    )
    assert second_res.status_code == 409
    assert "Duplicate message" in second_res.json()["detail"]

    # Message count should only be from the first request (1 user msg + 1 AI msg)
    assert (
        db_session.query(TicketMessage)
        .filter(TicketMessage.ticket_id == customer_ticket.id)
        .count()
        == 2
    )


def test_failure_rollback_behavior_without_partial_writes(
    customer_client,
    customer_ticket,
    db_session,
    monkeypatch,
):
    from backend.ai import service

    def exploding_specialist(*args, **kwargs):
        raise RuntimeError("Simulated unhandled failure")

    monkeypatch.setattr(
        service,
        "run_specialist_delegation",
        exploding_specialist,
    )

    with pytest.raises(RuntimeError, match="Simulated unhandled failure"):
        customer_client.post(
            f"/ai/tickets/{customer_ticket.id}/ai-reply",
            json={"message": "Where is my shipment?"},
        )

    # Transaction rolled back: 0 messages, 0 activities
    assert (
        db_session.query(TicketMessage)
        .filter(TicketMessage.ticket_id == customer_ticket.id)
        .count()
        == 0
    )
    assert (
        db_session.query(TicketActivity)
        .filter(TicketActivity.ticket_id == customer_ticket.id)
        .count()
        == 0
    )


def test_check_constraint_enforces_ai_null_and_human_non_null(
    db_session,
    customer_ticket,
):
    # Valid AI message: sender_id is None
    valid_ai = TicketMessage(
        ticket_id=customer_ticket.id,
        sender_id=None,
        sender_type="AI",
        content="I am an AI.",
    )
    db_session.add(valid_ai)
    db_session.commit()

    # Invalid: AI with non-null sender_id
    invalid_ai = TicketMessage(
        ticket_id=customer_ticket.id,
        sender_id=customer_ticket.customer_id,
        sender_type="AI",
        content="Invalid AI message.",
    )
    db_session.add(invalid_ai)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Invalid: CUSTOMER with NULL sender_id
    invalid_customer = TicketMessage(
        ticket_id=customer_ticket.id,
        sender_id=None,
        sender_type="CUSTOMER",
        content="Invalid customer message.",
    )
    db_session.add(invalid_customer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Invalid: ADMIN with NULL sender_id
    invalid_admin = TicketMessage(
        ticket_id=customer_ticket.id,
        sender_id=None,
        sender_type="ADMIN",
        content="Invalid admin message.",
    )
    db_session.add(invalid_admin)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_order_reply_does_not_disclose_another_customers_order(
    customer_client,
    customer_ticket,
    second_customer_order,
):
    response = customer_client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json={
            "message": (
                f"Check order status for "
                f"order #{second_customer_order.order_number}"
            )
        },
    )

    assert response.status_code == 200, response.text

    reply = response.json()["message_content"]

    assert "could not find that order" in reply
    assert second_customer_order.status not in reply
    assert second_customer_order.order_number not in reply


def test_real_jwt_authentication_allows_owner_reply(
    client,
    customer_user,
    customer_ticket,
):
    # Use client, not customer_client: get_current_user is not overridden.
    token = create_access_token(
        subject=str(customer_user.user_id),
        role=customer_user.role,
    )

    response = client.post(
        f"/ai/tickets/{customer_ticket.id}/ai-reply",
        json={"message": "Hello"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert (
        response.json()["action_taken"]
        == "REPLIED_VIA_GENERAL_SUPPORT"
    )