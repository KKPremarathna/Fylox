import logging
from typing import Any

import httpx
from google.genai import errors
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.activity.service import record_activity
from backend.ai.models import BillingAnalysisRecord
from backend.ai.provider import (
    execute_billing_analysis,
    generate_fallback_analysis,
)
from backend.ai.schemas import (
    BillingAgentOutput,
    BillingAnalysisResponse,
)
from backend.orders.service import get_order_for_owner_or_admin
from backend.payments.models import Payment
from backend.payments.service import check_duplicate_charges
from backend.policies.service import search_policies
from backend.tickets.models import Ticket
from backend.users.models import User


logger = logging.getLogger(__name__)


SAFE_PROVIDER_CODES = {
    "MISSING_API_KEY",
    "MISSING_MODEL",
    "UNSUPPORTED_PROVIDER",
    "NO_CANDIDATE",
    "INCOMPLETE_OR_BLOCKED_OUTPUT",
    "EMPTY_OUTPUT",
    "INVALID_EVIDENCE_IDS",
    "INVALID_POLICY_IDS",
}


class InvalidBillingOutput(ValueError):
    pass


def safe_failure_code(error: Exception) -> str:
    if isinstance(error, InvalidBillingOutput):
        return str(error)

    if isinstance(error, ValidationError):
        return "INVALID_PROVIDER_OUTPUT"

    if isinstance(error, (TimeoutError, httpx.TimeoutException)):
        return "PROVIDER_TIMEOUT"

    if isinstance(error, errors.APIError):
        if error.code == 429:
            return "PROVIDER_RATE_LIMITED"

        if error.code in (401, 403):
            return "PROVIDER_ACCESS_DENIED"

        return "PROVIDER_API_ERROR"

    if isinstance(error, httpx.RequestError):
        return "PROVIDER_CONNECTION_ERROR"

    if isinstance(error, ValueError):
        code = str(error)

        if code in SAFE_PROVIDER_CODES:
            return code

        return "INVALID_PROVIDER_OUTPUT"

    return "PROVIDER_ERROR"


def validate_provider_payload(
    raw: Any,
    valid_payment_ids: set[int],
    valid_policy_ids: set[int],
) -> tuple[BillingAgentOutput, str, str | None]:
    if not isinstance(raw, dict):
        raise InvalidBillingOutput("INVALID_PROVIDER_OUTPUT")

    source = raw.get("analysis_source")

    if source not in ("LLM", "FALLBACK"):
        raise InvalidBillingOutput("INVALID_ANALYSIS_SOURCE")

    fallback_reason = raw.get("fallback_reason")

    if source == "LLM" and fallback_reason is not None:
        raise InvalidBillingOutput("INVALID_ANALYSIS_SOURCE")

    if source == "FALLBACK":
        if fallback_reason != "LIVE_PROVIDER_DISABLED":
            raise InvalidBillingOutput("INVALID_FALLBACK_REASON")

    backend_fields = {
        "analysis_source",
        "fallback_reason",
        "requires_human_review",
    }

    content = {
        key: value
        for key, value in raw.items()
        if key not in backend_fields
    }

    output = BillingAgentOutput.model_validate(content)

    if not set(output.evidence_ids).issubset(valid_payment_ids):
        raise InvalidBillingOutput("INVALID_EVIDENCE_IDS")

    if not set(output.policy_source_ids).issubset(valid_policy_ids):
        raise InvalidBillingOutput("INVALID_POLICY_IDS")

    return output, source, fallback_reason


def run_billing_analysis(
    db: Session,
    ticket: Ticket,
    order_id: int,
    current_admin: User,
) -> BillingAnalysisResponse:
    order = get_order_for_owner_or_admin(
        db,
        order_id,
        current_admin,
    )

    if order.customer_id != ticket.customer_id:
        raise ValueError(
            "Selected order does not belong to the ticket customer."
        )

    payments = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .all()
    )

    valid_payment_ids = {
        payment.id for payment in payments
    }

    payment_check = check_duplicate_charges(
        order.id,
        payments,
    )

    sanitized_payment_findings = {
        "order_id": order.id,
        "has_possible_duplicate": (
            payment_check.has_possible_duplicate
        ),
        "successful_payment_count": (
            payment_check.successful_payment_count
        ),
        "message": payment_check.message,
        "payment_ids": sorted(valid_payment_ids),
    }

    policy_results = search_policies(
        db,
        ticket.description,
    )

    policies_data = [
        {
            "id": result.chunk_id,
            "text": result.snippet_text,
            "title": result.document_title,
        }
        for result in policy_results
    ]

    valid_policy_ids = {
        policy["id"] for policy in policies_data
    }

    try:
        raw = execute_billing_analysis(
            sanitized_payment_findings=(
                sanitized_payment_findings
            ),
            matching_policies=policies_data,
            ticket_text=ticket.description,
        )

        output, analysis_source, fallback_reason = (
            validate_provider_payload(
                raw,
                valid_payment_ids,
                valid_policy_ids,
            )
        )

    except (
        ValidationError,
        ValueError,
        TimeoutError,
        httpx.RequestError,
        errors.APIError,
    ) as error:
        fallback_reason = safe_failure_code(error)

        logger.warning(
            "Billing provider fallback: ticket_id=%s reason=%s",
            ticket.id,
            fallback_reason,
        )

        fallback = generate_fallback_analysis(
            sanitized_payment_findings,
            fallback_reason=fallback_reason,
        )

        fallback_content = {
            key: value
            for key, value in fallback.items()
            if key not in {
                "analysis_source",
                "fallback_reason",
                "requires_human_review",
            }
        }

        output = BillingAgentOutput.model_validate(
            fallback_content
        )

        analysis_source = "FALLBACK"

    record = BillingAnalysisRecord(
        ticket_id=ticket.id,
        order_id=order.id,
        admin_id=current_admin.user_id,
        summary=output.summary,
        recommended_next_steps=(
            output.recommended_next_steps
        ),
        reply_draft=output.reply_draft,
        evidence_ids=output.evidence_ids,
        policy_source_ids=output.policy_source_ids,
        requires_human_review=True,
        escalation_reason=output.escalation_reason,
        analysis_source=analysis_source,
        fallback_reason=fallback_reason,
    )

    db.add(record)
    db.flush()

    activity_message = (
        f"Admin {current_admin.username} generated an AI "
        f"Billing Analysis for Order #{order.order_number}"
    )

    record_activity(
        db=db,
        ticket_id=ticket.id,
        actor_id=current_admin.user_id,
        event_type="BILLING_ANALYSIS_GENERATED",
        message=activity_message,
    )

    db.commit()
    db.refresh(record)

    return BillingAnalysisResponse.model_validate(record)