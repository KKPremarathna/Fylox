from copy import deepcopy

import pytest

import backend.ai.billing_analysis as billing_service
from backend.activity.models import TicketActivity
from backend.ai.models import BillingAnalysisRecord
from backend.messages.models import TicketMessage


@pytest.fixture
def mock_billing_provider(monkeypatch):
    calls = []

    def fake_provider(
        sanitized_payment_findings,
        matching_policies,
        ticket_text,
    ):
        calls.append(ticket_text)

        return {
            "summary": sanitized_payment_findings.get(
                "message",
                "Payment evidence requires admin review.",
            ),
            "evidence_ids": list(
                sanitized_payment_findings.get("payment_ids", [])
            ),
            "policy_source_ids": [
                policy["id"] for policy in matching_policies
            ],
            "recommended_next_steps": [
                "Review the verified payment findings."
            ],
            "reply_draft": (
                "Your payment concern is being reviewed."
            ),
            "requires_human_review": False,
            "escalation_reason": None,
        }

    monkeypatch.setattr(
        billing_service,
        "execute_billing_analysis",
        fake_provider,
    )

    return fake_provider, calls


def request_analysis(client, ticket, order):
    return client.post(
        f"/ai/tickets/{ticket.id}/billing-analysis",
        json={"order_id": order.id},
    )


def test_admin_billing_analysis_success(
    admin_client,
    customer_ticket,
    customer_order,
    db_session,
    mock_billing_provider,
):
    before_messages = db_session.query(TicketMessage).filter_by(
        ticket_id=customer_ticket.id
    ).count()

    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["order_id"] == customer_order.id
    assert data["summary"]
    assert data["requires_human_review"] is True
    assert data["analysis_source"] == "LLM"
    assert data["admin_id"] is not None

    after_messages = db_session.query(TicketMessage).filter_by(
        ticket_id=customer_ticket.id
    ).count()

    assert after_messages == before_messages

    record = db_session.query(BillingAnalysisRecord).filter_by(
        id=data["id"]
    ).one()

    assert record.order_id == customer_order.id
    assert record.admin_id == data["admin_id"]
    assert record.requires_human_review is True

    activity = db_session.query(TicketActivity).filter_by(
        ticket_id=customer_ticket.id,
        event_type="BILLING_ANALYSIS_GENERATED",
    ).first()

    assert activity is not None
    assert "generated an AI Billing Analysis" in activity.message
    assert "{" not in activity.message


def test_customer_forbidden_billing_analysis(
    customer_client,
    customer_ticket,
    customer_order,
    mock_billing_provider,
):
    _, calls = mock_billing_provider

    resp = request_analysis(
        customer_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 403
    assert calls == []


def test_reject_other_customer_order(
    admin_client,
    customer_ticket,
    second_customer_order,
    mock_billing_provider,
):
    _, calls = mock_billing_provider

    resp = request_analysis(
        admin_client,
        customer_ticket,
        second_customer_order,
    )

    assert resp.status_code == 400
    assert "does not belong" in resp.json()["detail"]
    assert calls == []


@pytest.mark.parametrize(
    ("field", "reason_fragment"),
    [
        ("evidence_ids", "hallucinated evidence ID"),
        ("policy_source_ids", "hallucinated policy ID"),
    ],
)
def test_unknown_reference_triggers_fallback(
    admin_client,
    customer_ticket,
    customer_order,
    mock_billing_provider,
    monkeypatch,
    field,
    reason_fragment,
):
    fake_provider, _ = mock_billing_provider

    def invalid_reference_provider(**kwargs):
        result = deepcopy(fake_provider(**kwargs))

        if field == "evidence_ids":
            allowed_ids = kwargs[
                "sanitized_payment_findings"
            ].get("payment_ids", [])
        else:
            allowed_ids = [
                policy["id"]
                for policy in kwargs["matching_policies"]
            ]

        unknown_id = max([0, *allowed_ids]) + 1
        result[field] = [unknown_id]

        return result

    monkeypatch.setattr(
        billing_service,
        "execute_billing_analysis",
        invalid_reference_provider,
    )

    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["analysis_source"] == "FALLBACK"
    assert data["requires_human_review"] is True
    assert reason_fragment in data["fallback_reason"]


def test_provider_failure_triggers_fallback(
    admin_client,
    customer_ticket,
    customer_order,
    monkeypatch,
):
    def unavailable_provider(**kwargs):
        raise TimeoutError("Simulated provider timeout")

    monkeypatch.setattr(
        billing_service,
        "execute_billing_analysis",
        unavailable_provider,
    )

    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["analysis_source"] == "FALLBACK"
    assert data["requires_human_review"] is True
    assert "timeout" in data["fallback_reason"].lower()


def test_model_requires_review_false_overridden(
    admin_client,
    customer_ticket,
    customer_order,
    mock_billing_provider,
):
    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200
    assert resp.json()["requires_human_review"] is True