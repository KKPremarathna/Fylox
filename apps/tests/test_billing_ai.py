import sys
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from google.genai import errors
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps"))

from backend.ai import provider
from backend.ai.billing_analysis import (
    InvalidBillingOutput,
    safe_failure_code,
    validate_provider_payload,
)
from backend.ai.schemas import BillingAgentOutput


@pytest.fixture
def payment_findings():
    return {
        "order_id": 10,
        "payment_ids": [101, 102],
        "has_possible_duplicate": True,
        "successful_payment_count": 2,
    }


@pytest.fixture
def policies():
    return [
        {
            "id": 201,
            "title": "Duplicate-charge review",
            "text": (
                "Verify payment records before making a "
                "duplicate-charge determination. "
                "Human approval is required for a refund."
            ),
        }
    ]


@pytest.fixture
def valid_content():
    return {
        "summary": (
            "The supplied findings flag a possible duplicate "
            "for the selected order."
        ),
        "evidence_ids": [101, 102],
        "policy_source_ids": [201],
        "recommended_next_steps": [
            "Verify the underlying payment records.",
            "Request human review before a billing decision.",
        ],
        "reply_draft": (
            "Thank you for reporting your concern. "
            "The available findings require human review "
            "before a billing decision can be made."
        ),
        "escalation_reason": (
            "A possible duplicate requires verification "
            "and human review."
        ),
    }


def llm_payload(content):
    return {
        **content,
        "requires_human_review": True,
        "analysis_source": "LLM",
        "fallback_reason": None,
    }


def test_deterministic_provider_does_not_call_gemini(
    monkeypatch,
    payment_findings,
    policies,
):
    monkeypatch.setattr(
        provider.settings,
        "billing_ai_provider",
        "deterministic",
    )

    gemini_call = Mock(
        side_effect=AssertionError(
            "Deterministic mode must not call Gemini."
        )
    )
    monkeypatch.setattr(
        provider,
        "call_gemini_billing",
        gemini_call,
    )

    result = provider.execute_billing_analysis(
        sanitized_payment_findings=payment_findings,
        matching_policies=policies,
        ticket_text="I may have been charged twice.",
    )

    gemini_call.assert_not_called()

    assert result["analysis_source"] == "FALLBACK"
    assert result["fallback_reason"] == "LIVE_PROVIDER_DISABLED"
    assert result["requires_human_review"] is True
    assert result["evidence_ids"] == [101, 102]
    assert result["policy_source_ids"] == []

    output, source, reason = validate_provider_payload(
        result,
        valid_payment_ids={101, 102},
        valid_policy_ids={201},
    )

    assert isinstance(output, BillingAgentOutput)
    assert source == "FALLBACK"
    assert reason == "LIVE_PROVIDER_DISABLED"


def test_gemini_provider_passes_context_and_enforces_review(
    monkeypatch,
    payment_findings,
    policies,
    valid_content,
):
    monkeypatch.setattr(
        provider.settings,
        "billing_ai_provider",
        "gemini",
    )

    # Backend-owned metadata must override provider metadata.
    mocked_result = {
        **valid_content,
        "requires_human_review": False,
        "analysis_source": "FALLBACK",
        "fallback_reason": "UNTRUSTED_VALUE",
    }

    gemini_call = Mock(return_value=mocked_result)
    monkeypatch.setattr(
        provider,
        "call_gemini_billing",
        gemini_call,
    )

    ticket_text = "I may have been charged twice."

    result = provider.execute_billing_analysis(
        sanitized_payment_findings=payment_findings,
        matching_policies=policies,
        ticket_text=ticket_text,
    )

    gemini_call.assert_called_once_with(
        payment_evidence=payment_findings,
        policies=policies,
        ticket_text=ticket_text,
    )

    assert result["requires_human_review"] is True
    assert result["analysis_source"] == "LLM"
    assert result["fallback_reason"] is None


def test_valid_llm_payload_is_accepted(valid_content):
    output, source, reason = validate_provider_payload(
        llm_payload(valid_content),
        valid_payment_ids={101, 102},
        valid_policy_ids={201},
    )

    assert output.evidence_ids == [101, 102]
    assert output.policy_source_ids == [201]
    assert source == "LLM"
    assert reason is None


@pytest.mark.parametrize(
    ("field", "invalid_ids", "expected_code"),
    [
        (
            "evidence_ids",
            [999],
            "INVALID_EVIDENCE_IDS",
        ),
        (
            "policy_source_ids",
            [999],
            "INVALID_POLICY_IDS",
        ),
    ],
)
def test_unknown_ids_are_rejected(
    valid_content,
    field,
    invalid_ids,
    expected_code,
):
    payload = llm_payload(valid_content)
    payload[field] = invalid_ids

    with pytest.raises(
        InvalidBillingOutput,
        match=expected_code,
    ):
        validate_provider_payload(
            payload,
            valid_payment_ids={101, 102},
            valid_policy_ids={201},
        )


@pytest.mark.parametrize(
    ("source", "reason", "expected_code"),
    [
        (
            "UNKNOWN",
            None,
            "INVALID_ANALYSIS_SOURCE",
        ),
        (
            "LLM",
            "PROVIDER_TIMEOUT",
            "INVALID_ANALYSIS_SOURCE",
        ),
        (
            "FALLBACK",
            "PROVIDER_TIMEOUT",
            "INVALID_FALLBACK_REASON",
        ),
    ],
)
def test_invalid_source_metadata_is_rejected(
    valid_content,
    source,
    reason,
    expected_code,
):
    payload = {
        **valid_content,
        "analysis_source": source,
        "fallback_reason": reason,
    }

    with pytest.raises(
        InvalidBillingOutput,
        match=expected_code,
    ):
        validate_provider_payload(
            payload,
            valid_payment_ids={101, 102},
            valid_policy_ids={201},
        )


def test_extra_output_fields_are_rejected(valid_content):
    payload = llm_payload(valid_content)
    payload["refund_approved"] = True

    with pytest.raises(ValidationError):
        validate_provider_payload(
            payload,
            valid_payment_ids={101, 102},
            valid_policy_ids={201},
        )


def test_payment_ids_must_be_integers(valid_content):
    payload = llm_payload(valid_content)
    payload["evidence_ids"] = ["101"]

    with pytest.raises(ValidationError):
        validate_provider_payload(
            payload,
            valid_payment_ids={101, 102},
            valid_policy_ids={201},
        )


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (
            TimeoutError(),
            "PROVIDER_TIMEOUT",
        ),
        (
            httpx.ReadTimeout("Synthetic timeout"),
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
        (
            ValueError("PRIVATE_PROVIDER_DETAILS"),
            "INVALID_PROVIDER_OUTPUT",
        ),
        (
            RuntimeError("PRIVATE_INTERNAL_DETAILS"),
            "PROVIDER_ERROR",
        ),
    ],
)
def test_safe_failure_codes(error, expected_code):
    assert safe_failure_code(error) == expected_code


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (429, "PROVIDER_RATE_LIMITED"),
        (401, "PROVIDER_ACCESS_DENIED"),
        (403, "PROVIDER_ACCESS_DENIED"),
        (500, "PROVIDER_API_ERROR"),
    ],
)
def test_api_error_status_mapping(status_code, expected_code):
    # Use an APIError-spec mock without relying on SDK constructors.
    error = Mock(spec=errors.APIError)
    error.code = status_code

    assert isinstance(error, errors.APIError)
    assert safe_failure_code(error) == expected_code


def test_validation_error_has_safe_code():
    with pytest.raises(ValidationError) as captured:
        BillingAgentOutput.model_validate({})

    assert (
        safe_failure_code(captured.value)
        == "INVALID_PROVIDER_OUTPUT"
    )


def test_fallback_content_is_schema_valid(payment_findings):
    result = provider.generate_fallback_analysis(
        payment_findings,
        fallback_reason="PROVIDER_TIMEOUT",
    )

    metadata_fields = {
        "analysis_source",
        "fallback_reason",
        "requires_human_review",
    }

    content = {
        key: value
        for key, value in result.items()
        if key not in metadata_fields
    }

    output = BillingAgentOutput.model_validate(content)

    assert output.evidence_ids == [101, 102]
    assert output.policy_source_ids == []
    assert result["analysis_source"] == "FALLBACK"
    assert result["fallback_reason"] == "PROVIDER_TIMEOUT"
    assert result["requires_human_review"] is True
    assert output.escalation_reason