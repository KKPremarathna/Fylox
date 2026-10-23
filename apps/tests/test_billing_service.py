import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps"))

from backend.ai import billing_analysis as service


@pytest.fixture
def service_context(monkeypatch):
    db = Mock()

    ticket = SimpleNamespace(
        id=30,
        customer_id=7,
        subject="Possible duplicate charge",
        description="I believe I was billed twice.",
    )

    order = SimpleNamespace(
        id=10,
        customer_id=7,
        order_number="FY-1001",
    )

    admin = SimpleNamespace(
        user_id=99,
        username="test_admin",
    )

    payments = [
        SimpleNamespace(id=101),
        SimpleNamespace(id=102),
    ]

    db.query.return_value.filter.return_value.all.return_value = (
        payments
    )

    order_lookup = Mock(return_value=order)
    monkeypatch.setattr(
        service,
        "get_order_for_owner_or_admin",
        order_lookup,
    )

    monkeypatch.setattr(
        service,
        "check_duplicate_charges",
        Mock(
            return_value=SimpleNamespace(
                has_possible_duplicate=True,
                successful_payment_count=2,
                message="Possible duplicate requires review.",
            )
        ),
    )

    policy_search = Mock(
        return_value=[
            SimpleNamespace(
                chunk_id=201,
                snippet_text="Human review is required.",
                document_title="Duplicate-charge policy",
            )
        ]
    )
    monkeypatch.setattr(
        service,
        "search_policies",
        policy_search,
    )

    # Capture record fields without requiring ORM persistence.
    record_factory = Mock(
        side_effect=lambda **fields: SimpleNamespace(
            id=500,
            **fields,
        )
    )
    monkeypatch.setattr(
        service,
        "BillingAnalysisRecord",
        record_factory,
    )

    activity = Mock()
    monkeypatch.setattr(
        service,
        "record_activity",
        activity,
    )

    # Every test must explicitly configure the provider behavior.
    provider_call = Mock(
        side_effect=AssertionError(
            "Provider behavior was not configured."
        )
    )
    monkeypatch.setattr(
        service,
        "execute_billing_analysis",
        provider_call,
    )

    return SimpleNamespace(
        db=db,
        ticket=ticket,
        order=order,
        admin=admin,
        order_lookup=order_lookup,
        policy_search=policy_search,
        provider_call=provider_call,
        record_factory=record_factory,
        activity=activity,
    )


def valid_provider_payload():
    return {
        "summary": (
            "The supplied findings flag a possible duplicate "
            "for the selected order."
        ),
        "evidence_ids": [101, 102],
        "policy_source_ids": [201],
        "recommended_next_steps": [
            "Verify the payment records before a decision."
        ],
        "reply_draft": (
            "Your billing concern requires human review."
        ),
        "escalation_reason": (
            "Possible duplicate requires verification."
        ),
        "requires_human_review": False,
        "analysis_source": "LLM",
        "fallback_reason": None,
    }


def run_analysis(context):
    return service.run_billing_analysis(
        db=context.db,
        ticket=context.ticket,
        order_id=context.order.id,
        current_admin=context.admin,
    )


def assert_record_and_activity_saved(context, response):
    record = context.db.add.call_args.args[0]

    assert record.requires_human_review is True
    assert record.ticket_id == context.ticket.id
    assert record.order_id == context.order.id
    assert record.admin_id == context.admin.user_id

    context.db.add.assert_called_once_with(record)
    context.db.flush.assert_called_once_with()
    context.db.commit.assert_called_once_with()
    context.db.refresh.assert_called_once_with(record)

    context.activity.assert_called_once_with(
        db=context.db,
        ticket_id=context.ticket.id,
        actor_id=context.admin.user_id,
        event_type="BILLING_ANALYSIS_GENERATED",
        message=(
            "Admin test_admin generated an AI "
            "Billing Analysis for Order #FY-1001"
        ),
    )

    assert response.id == 500
    assert response.requires_human_review is True


def test_successful_analysis_enforces_review_and_saves(
    service_context,
):
    context = service_context
    context.provider_call.side_effect = None
    context.provider_call.return_value = valid_provider_payload()

    response = run_analysis(context)

    assert response.analysis_source == "LLM"
    assert response.fallback_reason is None
    assert response.evidence_ids == [101, 102]
    assert response.policy_source_ids == [201]

    expected_ticket_text = (
        "Possible duplicate charge\n"
        "I believe I was billed twice."
    )

    context.policy_search.assert_called_once_with(
        context.db,
        expected_ticket_text,
    )

    provider_arguments = context.provider_call.call_args.kwargs

    assert provider_arguments["ticket_text"] == expected_ticket_text
    assert (
        provider_arguments["sanitized_payment_findings"][
            "payment_ids"
        ]
        == [101, 102]
    )

    assert_record_and_activity_saved(context, response)


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (
            TimeoutError(),
            "PROVIDER_TIMEOUT",
        ),
        (
            httpx.ConnectError("Synthetic connection failure"),
            "PROVIDER_CONNECTION_ERROR",
        ),
        (
            ValueError("MISSING_API_KEY"),
            "MISSING_API_KEY",
        ),
    ],
)
def test_provider_failure_generates_and_saves_fallback(
    service_context,
    error,
    expected_reason,
):
    context = service_context
    context.provider_call.side_effect = error

    response = run_analysis(context)

    assert response.analysis_source == "FALLBACK"
    assert response.fallback_reason == expected_reason
    assert response.evidence_ids == [101, 102]
    assert response.policy_source_ids == []

    assert_record_and_activity_saved(context, response)


@pytest.mark.parametrize(
    ("field", "expected_reason"),
    [
        ("evidence_ids", "INVALID_EVIDENCE_IDS"),
        ("policy_source_ids", "INVALID_POLICY_IDS"),
    ],
)
def test_invalid_provider_ids_trigger_saved_fallback(
    service_context,
    field,
    expected_reason,
):
    context = service_context

    payload = valid_provider_payload()
    payload[field] = [999]

    context.provider_call.side_effect = None
    context.provider_call.return_value = payload

    response = run_analysis(context)

    assert response.analysis_source == "FALLBACK"
    assert response.fallback_reason == expected_reason
    assert response.evidence_ids == [101, 102]
    assert response.policy_source_ids == []

    assert_record_and_activity_saved(context, response)


def test_other_customers_order_is_rejected_before_provider_call(
    service_context,
):
    context = service_context
    context.order.customer_id = 12345

    with pytest.raises(
        ValueError,
        match="Selected order does not belong",
    ):
        run_analysis(context)

    context.provider_call.assert_not_called()
    context.policy_search.assert_not_called()
    context.record_factory.assert_not_called()
    context.activity.assert_not_called()

    context.db.query.assert_not_called()
    context.db.add.assert_not_called()
    context.db.commit.assert_not_called()