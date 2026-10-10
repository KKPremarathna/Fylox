from sqlalchemy.orm import Session

from backend.ai.models import BillingAnalysisRecord
from backend.ai.provider import (
    execute_billing_analysis,
    generate_fallback_analysis,
)
from backend.ai.schemas import BillingAnalysisResponse
from backend.activity.service import record_activity
from backend.orders.service import get_order_for_owner_or_admin
from backend.payments.models import Payment
from backend.payments.service import check_duplicate_charges
from backend.policies.models import PolicyChunk
from backend.policies.service import search_policies
from backend.tickets.models import Ticket
from backend.users.models import User


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

    valid_payment_ids = {payment.id for payment in payments}

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

    valid_policy_ids = set()
    policies_data = []

    # Transitional lookup: replace with source IDs from policy search.
    for result in policy_results:
        chunk = (
            db.query(PolicyChunk)
            .filter(
                PolicyChunk.content_snippet == result.snippet_text
            )
            .first()
        )

        if chunk is not None:
            valid_policy_ids.add(chunk.id)

            policies_data.append(
                {
                    "id": chunk.id,
                    "text": chunk.content_snippet,
                    "title": result.document_title,
                }
            )

    try:
        raw_llm_dict = execute_billing_analysis(
            sanitized_payment_findings=(
                sanitized_payment_findings
            ),
            matching_policies=policies_data,
            ticket_text=ticket.description,
        )

        essential_keys = [
            "summary",
            "evidence_ids",
            "policy_source_ids",
            "recommended_next_steps",
            "reply_draft",
        ]

        if not all(
            key in raw_llm_dict for key in essential_keys
        ):
            raise ValueError("Provider Output Missing Keys")

        for evidence_id in raw_llm_dict["evidence_ids"]:
            if evidence_id not in valid_payment_ids:
                raise ValueError(
                    "Provider hallucinated evidence ID "
                    f"{evidence_id}"
                )

        for policy_id in raw_llm_dict["policy_source_ids"]:
            if policy_id not in valid_policy_ids:
                raise ValueError(
                    "Provider hallucinated policy ID "
                    f"{policy_id}"
                )

        analysis_source = raw_llm_dict.get(
            "analysis_source",
            "LLM",
        )

        fallback_reason = raw_llm_dict.get(
            "fallback_reason"
        )

        escalation_reason = raw_llm_dict.get(
            "escalation_reason"
        )

    except Exception as error:
        # Transitional behavior; safe error mapping is the next step.
        fallback_reason = str(error)

        raw_llm_dict = generate_fallback_analysis(
            sanitized_payment_findings,
            fallback_reason=fallback_reason,
        )

        analysis_source = "FALLBACK"

        escalation_reason = (
            "AI analysis could not be completed. "
            "Human review is required."
        )

    record = BillingAnalysisRecord(
        ticket_id=ticket.id,
        order_id=order.id,
        admin_id=current_admin.user_id,
        summary=raw_llm_dict["summary"],
        recommended_next_steps=(
            raw_llm_dict["recommended_next_steps"]
        ),
        reply_draft=raw_llm_dict["reply_draft"],
        evidence_ids=raw_llm_dict["evidence_ids"],
        policy_source_ids=raw_llm_dict["policy_source_ids"],
        requires_human_review=True,
        escalation_reason=escalation_reason,
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