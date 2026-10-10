import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr, ValidationError

import backend.ai.provider as provider


@pytest.fixture
def gemini_setup(monkeypatch):
    monkeypatch.setattr(
        provider.settings,
        "gemini_api_key",
        SecretStr("fake-test-key"),
    )

    monkeypatch.setattr(
        provider.settings,
        "gemini_model",
        "fake-test-model",
    )

    client_factory = MagicMock()

    client = (
        client_factory.return_value
        .__enter__.return_value
    )

    monkeypatch.setattr(
        provider.genai,
        "Client",
        client_factory,
    )

    payload = {
        "summary": "One successful payment requires review.",
        "evidence_ids": [10],
        "policy_source_ids": [20],
        "recommended_next_steps": [
            "Review the supplied payment findings."
        ],
        "reply_draft": (
            "We are reviewing your payment concern."
        ),
        "escalation_reason": None,
    }

    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                finish_reason=(
                    provider.types.FinishReason.STOP
                )
            )
        ],
        text=json.dumps(payload),
    )

    client.models.generate_content.return_value = response

    return SimpleNamespace(
        factory=client_factory,
        client=client,
        payload=payload,
        response=response,
        evidence={
            "payment_ids": [10],
            "has_possible_duplicate": False,
            "successful_payment_count": 1,
        },
        policies=[
            {
                "id": 20,
                "title": "Demo refund review policy",
                "text": "Refunds require human approval.",
            }
        ],
    )


def analyze(setup):
    return provider.call_gemini_billing(
        payment_evidence=setup.evidence,
        policies=setup.policies,
    )


def test_gemini_valid_output(gemini_setup):
    result = analyze(gemini_setup)

    assert result["evidence_ids"] == [10]
    assert result["policy_source_ids"] == [20]
    assert "requires_human_review" not in result

    generate = (
        gemini_setup.client.models.generate_content
    )

    generate.assert_called_once()

    kwargs = generate.call_args.kwargs

    assert kwargs["model"] == "fake-test-model"

    assert (
        kwargs["config"].response_mime_type
        == "application/json"
    )

    sent_context = json.loads(kwargs["contents"])

    assert sent_context["allowed_evidence_ids"] == [10]
    assert "ticket_text" not in sent_context

    http_options = (
        gemini_setup.factory.call_args.kwargs[
            "http_options"
        ]
    )

    assert http_options.retry_options.attempts == 1


@pytest.mark.parametrize(
    ("setting_name", "empty_value", "expected_error"),
    [
        (
            "gemini_api_key",
            SecretStr(""),
            "MISSING_API_KEY",
        ),
        (
            "gemini_model",
            "",
            "MISSING_MODEL",
        ),
    ],
)
def test_missing_configuration(
    gemini_setup,
    monkeypatch,
    setting_name,
    empty_value,
    expected_error,
):
    monkeypatch.setattr(
        provider.settings,
        setting_name,
        empty_value,
    )

    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        analyze(gemini_setup)

    gemini_setup.factory.assert_not_called()


@pytest.mark.parametrize(
    ("field", "expected_error"),
    [
        (
            "evidence_ids",
            "INVALID_EVIDENCE_IDS",
        ),
        (
            "policy_source_ids",
            "INVALID_POLICY_IDS",
        ),
    ],
)
def test_unknown_references(
    gemini_setup,
    field,
    expected_error,
):
    gemini_setup.payload[field] = [9999]

    gemini_setup.response.text = json.dumps(
        gemini_setup.payload
    )

    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        analyze(gemini_setup)


def test_invalid_output_type(gemini_setup):
    gemini_setup.payload["summary"] = 123

    gemini_setup.response.text = json.dumps(
        gemini_setup.payload
    )

    with pytest.raises(ValidationError):
        analyze(gemini_setup)


def test_empty_output(gemini_setup):
    gemini_setup.response.text = ""

    with pytest.raises(
        ValueError,
        match="EMPTY_OUTPUT",
    ):
        analyze(gemini_setup)


def test_no_candidate(gemini_setup):
    gemini_setup.response.candidates = []

    with pytest.raises(
        ValueError,
        match="NO_CANDIDATE",
    ):
        analyze(gemini_setup)


def test_incomplete_output(gemini_setup):
    gemini_setup.response.candidates[
        0
    ].finish_reason = (
        provider.types.FinishReason.MAX_TOKENS
    )

    with pytest.raises(
        ValueError,
        match="INCOMPLETE_OR_BLOCKED_OUTPUT",
    ):
        analyze(gemini_setup)


def test_timeout_propagates(gemini_setup):
    generate = (
        gemini_setup.client.models.generate_content
    )

    generate.side_effect = TimeoutError(
        "Synthetic timeout"
    )

    with pytest.raises(TimeoutError):
        analyze(gemini_setup)


def test_deterministic_mode_skips_gemini(
    gemini_setup,
    monkeypatch,
):
    monkeypatch.setattr(
        provider.settings,
        "billing_ai_provider",
        "deterministic",
    )

    result = provider.execute_billing_analysis(
        sanitized_payment_findings=(
            gemini_setup.evidence
        ),
        matching_policies=gemini_setup.policies,
        ticket_text="Synthetic billing concern",
    )

    assert result["analysis_source"] == "FALLBACK"

    assert (
        result["fallback_reason"]
        == "LIVE_PROVIDER_DISABLED"
    )

    assert result["requires_human_review"] is True

    gemini_setup.factory.assert_not_called()


def test_gemini_mode_uses_live_adapter(
    gemini_setup,
    monkeypatch,
):
    monkeypatch.setattr(
        provider.settings,
        "billing_ai_provider",
        "gemini",
    )

    result = provider.execute_billing_analysis(
        sanitized_payment_findings=(
            gemini_setup.evidence
        ),
        matching_policies=gemini_setup.policies,
        ticket_text="Synthetic billing concern",
    )

    assert result["analysis_source"] == "LLM"
    assert result["fallback_reason"] is None
    assert result["requires_human_review"] is True

    (
        gemini_setup.client.models.generate_content
        .assert_called_once()
    )


def test_gemini_mode_error_reaches_service(
    gemini_setup,
    monkeypatch,
):
    monkeypatch.setattr(
        provider.settings,
        "billing_ai_provider",
        "gemini",
    )

    generate = (
        gemini_setup.client.models.generate_content
    )

    generate.side_effect = TimeoutError(
        "Synthetic timeout"
    )

    with pytest.raises(TimeoutError):
        provider.execute_billing_analysis(
            sanitized_payment_findings=(
                gemini_setup.evidence
            ),
            matching_policies=gemini_setup.policies,
            ticket_text="Synthetic billing concern",
        )