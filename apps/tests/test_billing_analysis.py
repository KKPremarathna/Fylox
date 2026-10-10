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
        calls.append(
            {
                "ticket_text": ticket_text,
                "policies": deepcopy(matching_policies),
            }
        )

        return {
            "summary": sanitized_payment_findings.get(
                "message",
                "Payment evidence requires admin review.",
            ),
            "evidence_ids": list(
                sanitized_payment_findings.get(
                    "payment_ids",
                    [],
                )
            ),
            "policy_source_ids": [
                policy["id"]
                for policy in matching_policies
            ],
            "recommended_next_steps": [
                "Review the verified payment findings."
            ],
            "reply_draft": (
                "Your payment concern is being reviewed."
            ),
            "requires_human_review": False,
            "escalation_reason": None,
            "analysis_source": "LLM",
            "fallback_reason": None,
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
    before_messages = (
        db_session.query(TicketMessage)
        .filter_by(ticket_id=customer_ticket.id)
        .count()
    )

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
    assert data["fallback_reason"] is None
    assert data["admin_id"] is not None

    after_messages = (
        db_session.query(TicketMessage)
        .filter_by(ticket_id=customer_ticket.id)
        .count()
    )

    assert after_messages == before_messages

    record = (
        db_session.query(BillingAnalysisRecord)
        .filter_by(id=data["id"])
        .one()
    )

    assert record.order_id == customer_order.id
    assert record.admin_id == data["admin_id"]
    assert record.requires_human_review is True

    activity = (
        db_session.query(TicketActivity)
        .filter_by(
            ticket_id=customer_ticket.id,
            event_type="BILLING_ANALYSIS_GENERATED",
        )
        .first()
    )

    assert activity is not None
    assert activity.actor_id == data["admin_id"]

    assert (
        "generated an AI Billing Analysis"
        in activity.message
    )

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
    ("field", "expected_reason"),
    [
        ("evidence_ids", "INVALID_EVIDENCE_IDS"),
        ("policy_source_ids", "INVALID_POLICY_IDS"),
    ],
)
def test_unknown_reference_triggers_fallback(
    admin_client,
    customer_ticket,
    customer_order,
    mock_billing_provider,
    monkeypatch,
    field,
    expected_reason,
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
    assert data["fallback_reason"] == expected_reason

    if field == "policy_source_ids":
        assert data["policy_source_ids"] == []


def test_provider_failure_triggers_fallback(
    admin_client,
    customer_ticket,
    customer_order,
    monkeypatch,
):
    private_error = "Synthetic timeout; secret=fake-private-value"

    def unavailable_provider(**kwargs):
        raise TimeoutError(private_error)

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
    assert data["fallback_reason"] == "PROVIDER_TIMEOUT"

    assert private_error not in resp.text
    assert "fake-private-value" not in resp.text


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


@pytest.mark.parametrize(
    ("field", "value", "expected_reason"),
    [
        (
            "summary",
            123,
            "INVALID_PROVIDER_OUTPUT",
        ),
        (
            "recommended_next_steps",
            "Review manually",
            "INVALID_PROVIDER_OUTPUT",
        ),
        (
            "analysis_source",
            "UNKNOWN",
            "INVALID_ANALYSIS_SOURCE",
        ),
        (
            "unexpected_field",
            "not allowed",
            "INVALID_PROVIDER_OUTPUT",
        ),
        (
            "fallback_reason",
            "untrusted provider details",
            "INVALID_ANALYSIS_SOURCE",
        ),
    ],
)
def test_invalid_payload_triggers_safe_fallback(
    admin_client,
    customer_ticket,
    customer_order,
    mock_billing_provider,
    monkeypatch,
    field,
    value,
    expected_reason,
):
    fake_provider, _ = mock_billing_provider

    def invalid_provider(**kwargs):
        result = deepcopy(fake_provider(**kwargs))
        result[field] = value
        return result

    monkeypatch.setattr(
        billing_service,
        "execute_billing_analysis",
        invalid_provider,
    )

    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["analysis_source"] == "FALLBACK"
    assert data["fallback_reason"] == expected_reason
    assert data["requires_human_review"] is True

    assert "unexpected_field" not in data


def test_deterministic_fallback_source_is_preserved(
    admin_client,
    customer_ticket,
    customer_order,
    monkeypatch,
):
    def deterministic_provider(
        sanitized_payment_findings,
        matching_policies,
        ticket_text,
    ):
        return billing_service.generate_fallback_analysis(
            sanitized_payment_findings,
            fallback_reason="LIVE_PROVIDER_DISABLED",
        )

    monkeypatch.setattr(
        billing_service,
        "execute_billing_analysis",
        deterministic_provider,
    )

    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["analysis_source"] == "FALLBACK"
    assert data["fallback_reason"] == "LIVE_PROVIDER_DISABLED"
    assert data["requires_human_review"] is True


def test_policy_chunk_id_is_used_directly(
    admin_client,
    customer_ticket,
    customer_order,
    mock_billing_provider,
    monkeypatch,
):
    from types import SimpleNamespace

    _, calls = mock_billing_provider

    fake_search_result = SimpleNamespace(
        chunk_id=2468,
        document_id=1357,
        snippet_text="Synthetic policy requires human review.",
        document_title="Synthetic billing policy",
    )

    monkeypatch.setattr(
        billing_service,
        "search_policies",
        lambda db, query: [fake_search_result],
    )

    resp = request_analysis(
        admin_client,
        customer_ticket,
        customer_order,
    )

    assert resp.status_code == 200
    assert resp.json()["policy_source_ids"] == [2468]

    assert calls[0]["policies"] == [
        {
            "id": 2468,
            "text": "Synthetic policy requires human review.",
            "title": "Synthetic billing policy",
        }
    ]