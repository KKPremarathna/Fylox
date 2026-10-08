import json
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.tickets.models import Ticket
from backend.orders.models import Order
from backend.payments.models import Payment
from backend.policies.models import PolicyChunk
from backend.users.models import User
from backend.ai.models import BillingAnalysisRecord
from backend.ai.schemas import BillingAnalysisResponse

from backend.orders.service import get_order_for_owner_or_admin
from backend.payments.service import check_duplicate_charges
from backend.policies.service import search_policies
from backend.activity.service import record_activity
from backend.ai.provider import execute_billing_analysis, generate_fallback_analysis


def run_billing_analysis(
    db: Session, 
    ticket: Ticket, 
    order_id: int, 
    current_admin: User
) -> BillingAnalysisResponse:
    # 1. Authorize order belongs to ticket customer
    # get_order_for_owner_or_admin allows admin, but we must verify it belongs to the customer
    order = get_order_for_owner_or_admin(db, order_id, current_admin)
    if order.customer_id != ticket.customer_id:
        raise ValueError("Selected order does not belong to the ticket customer.")

    # 2. Fetch payments for the order
    payments = db.query(Payment).filter(Payment.order_id == order.id).all()
    valid_payment_ids = {p.id for p in payments}
    
    payment_check = check_duplicate_charges(order.id, payments)
    
    sanitized_payment_findings = {
        "order_id": order.id,
        "has_possible_duplicate": payment_check.has_possible_duplicate,
        "successful_payment_count": payment_check.successful_payment_count,
        "message": payment_check.message,
        "payment_ids": list(valid_payment_ids)
    }

    # 3. Retrieve Policies
    policy_results = search_policies(db, ticket.description)
    
    # We need valid policy chunk IDs for validation, which search_policies doesn't export directly in V1.
    # We will look them up by text/heading match to ensure strict ID validation.
    valid_policy_ids = set()
    policies_data = []
    
    for rp in policy_results:
        # Find the chunk
        chunk = db.query(PolicyChunk).filter(PolicyChunk.content_snippet == rp.snippet_text).first()
        if chunk:
            valid_policy_ids.add(chunk.id)
            policies_data.append({"id": chunk.id, "text": chunk.content_snippet, "title": rp.document_title})

    try:
        raw_llm_dict = execute_billing_analysis(
            sanitized_payment_findings=sanitized_payment_findings, 
            matching_policies=policies_data,
            ticket_text=ticket.description
        )
        
        # 4. Strict Validation of output
        essential_keys = ["summary", "evidence_ids", "policy_source_ids", "recommended_next_steps", "reply_draft"]
        if not all(k in raw_llm_dict for k in essential_keys):
            raise Exception("Provider Output Missing Keys")
            
        # Verify evidence_ids
        for ev_id in raw_llm_dict.get("evidence_ids", []):
            if ev_id not in valid_payment_ids:
                raise Exception(f"Provider hallucinated evidence ID {ev_id}")
                
        # Verify policy_source_ids
        for pol_id in raw_llm_dict.get("policy_source_ids", []):
            if pol_id not in valid_policy_ids:
                raise Exception(f"Provider hallucinated policy ID {pol_id}")

        analysis_source = "LLM"
        fallback_reason = None
        
        # Enforce requires_human_review=True in backend logic always for V2 safe slice
        requires_review = True
        
        escalation_reason = raw_llm_dict.get("escalation_reason")

    except Exception as e:
        raw_llm_dict = generate_fallback_analysis(
            sanitized_payment_findings,
            fallback_reason=str(e)
        )
        analysis_source = "FALLBACK"
        fallback_reason = str(e)
        requires_review = True
        escalation_reason = "System automatically escalated due to validation failure."

    # 5. Persist the dedicated Record
    record = BillingAnalysisRecord(
        ticket_id=ticket.id,
        order_id=order.id,
        admin_id=current_admin.user_id,
        summary=raw_llm_dict["summary"],
        recommended_next_steps=raw_llm_dict["recommended_next_steps"],
        reply_draft=raw_llm_dict["reply_draft"],
        evidence_ids=raw_llm_dict["evidence_ids"],
        policy_source_ids=raw_llm_dict["policy_source_ids"],
        requires_human_review=requires_review,
        escalation_reason=escalation_reason,
        analysis_source=analysis_source,
        fallback_reason=fallback_reason
    )
    db.add(record)
    db.flush() # get record.id

    # 6. Minimal TicketActivity audit event without storing full JSON
    activity_msg = f"Admin {current_admin.username} generated an AI Billing Analysis for Order #{order.order_number}"
    record_activity(
        db=db,
        ticket_id=ticket.id,
        actor_id=current_admin.user_id,
        event_type="BILLING_ANALYSIS_GENERATED",
        message=activity_msg
    )
    
    db.commit()
    db.refresh(record)

    return BillingAnalysisResponse.model_validate(record)
