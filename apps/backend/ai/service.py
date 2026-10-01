from sqlalchemy.orm import Session
from backend.ai.classifier import classify_message
from backend.ai.schemas import AIReplyResponse, ClassifyRequest
from backend.ai.specialists import run_specialist_delegation
from backend.activity.models import TicketActivity
from backend.messages.models import TicketMessage
from backend.tickets.models import Ticket
import json


def execute_triage(payload: ClassifyRequest) -> AIReplyResponse:
    """
    Stand-alone execution for pure classification safely. No DB writes.
    """
    decision = classify_message(payload.message)
    return AIReplyResponse(
        message_content=None,
        routing_decision=decision,
        action_taken="CLASSIFIED_ONLY"
    )


def process_ticket_ai_reply(db: Session, ticket: Ticket, message: str) -> AIReplyResponse:
    """
    Full pipeline routing: classifies message, executes strictly authorized specialist,
    writes safe messages directly into execution context, logs explicitly to audit tracing.
    """
    decision = classify_message(message)
    category = decision.category
    
    # 1. Log Routing Decision (Audit Layer)
    activity = TicketActivity(
        ticket_id=ticket.id,
        actor_id=None, 
        event_type="AI_ROUTED",
        message=json.dumps({
            "category": category.value,
            "confidence": decision.confidence,
            "classifier_type": decision.classifier_type,
            "escalation_reason": decision.escalation_reason,
            "actor_role": "SYSTEM"
        })
    )
    db.add(activity)

    # 2. Invoke Specialist Boundary Safely
    # Only applies domain specific replies if safely within the generated boundaries.
    reply_content = run_specialist_delegation(db, category, message, ticket.customer_id)

    action_taken = "ROUTED_WITHOUT_REPLY"

    if reply_content:
        # Guarantee no sensitive payloads leaked beyond read-only text summaries 
        # mapped cleanly for ORDER_SUPPORT, POLICY_SUPPORT, GENERAL_SUPPORT allowed behaviors.
        new_msg = TicketMessage(
            ticket_id=ticket.id,
            sender_id=ticket.customer_id,
            sender_type="AI",
            content=reply_content
        )
        db.add(new_msg)
        action_taken = f"REPLIED_VIA_{category.value}"

    db.commit()
    return AIReplyResponse(
        message_content=reply_content,
        routing_decision=decision,
        action_taken=action_taken
    )
