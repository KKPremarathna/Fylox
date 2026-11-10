import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.activity.models import TicketActivity
from backend.activity.service import record_activity
from backend.ai.classifier import classify_message
from backend.ai.schemas import AIReplyResponse, ClassifyRequest
from backend.ai.specialists import run_specialist_delegation
from backend.messages.models import TicketMessage
from backend.messages.schemas import TicketMessageResponse
from backend.tickets.models import Ticket
from backend.users.models import User


def execute_triage(payload: ClassifyRequest) -> AIReplyResponse:
    """
    Stand-alone execution for pure classification safely. No DB writes.
    """
    decision = classify_message(payload.message)
    return AIReplyResponse(
        message_content=None,
        routing_decision=decision,
        action_taken="CLASSIFIED_ONLY",
    )


def process_ticket_ai_reply(
    db: Session,
    ticket: Ticket,
    message: str,
    current_user: User,
    client_token: Optional[str] = None,
) -> AIReplyResponse:
    """
    Single backend orchestration pipeline for AI ticket interaction:
    1. Validates submitted input (rejects empty or whitespace-only messages).
    2. Detects and prevents duplicate rapid submissions / retries.
    3. Saves customer or admin input under their actual authenticated identity.
    4. Records activity event for user message creation.
    5. Runs deterministic classification and logs routing decision.
    6. Dispatches to specialist scoped strictly to the ticket's customer.
    7. If an automated reply is produced, saves the AI response with sender_id=NULL and sender_type='AI'.
    8. Ensures transactional atomicity with rollback on failure.
    """
    cleaned_message = message.strip()
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Message cannot be empty or whitespace only.",
        )

    # Duplicate / retry prevention:
    # Check if this user recently submitted an identical message on this ticket within 5 seconds
    recent_stmt = (
        select(TicketMessage)
        .where(
            TicketMessage.ticket_id == ticket.id,
            TicketMessage.sender_id == current_user.user_id,
            TicketMessage.sender_type == current_user.role,
            TicketMessage.content == cleaned_message,
        )
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
        .limit(1)
    )
    last_identical = db.scalars(recent_stmt).first()
    if last_identical is not None:
        now = datetime.now(timezone.utc)
        created = last_identical.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if (now - created).total_seconds() < 5.0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate message submission detected. Please wait a moment before resubmitting.",
            )

    try:
        # 1. Save user submitted input under actual authenticated user
        user_msg = TicketMessage(
            ticket_id=ticket.id,
            sender_id=current_user.user_id,
            sender_type=current_user.role,
            content=cleaned_message,
        )
        db.add(user_msg)

        # Activity log for user message
        activity_msg = (
            "Admin added a message."
            if current_user.role == "ADMIN"
            else "Customer added a message."
        )
        record_activity(
            db=db,
            ticket_id=ticket.id,
            actor_id=current_user.user_id,
            event_type="MESSAGE_CREATED",
            message=activity_msg,
        )

        # 2. Routing Decision
        decision = classify_message(cleaned_message)
        category = decision.category

        # Audit log for routing decision
        activity = TicketActivity(
            ticket_id=ticket.id,
            actor_id=None,
            event_type="AI_ROUTED",
            message=json.dumps({
                "category": category.value,
                "confidence": decision.confidence,
                "classifier_type": decision.classifier_type,
                "escalation_reason": decision.escalation_reason,
                "actor_role": "SYSTEM",
            }),
        )
        db.add(activity)

        # 3. Specialist Delegation scoped strictly to ticket customer
        reply_content = run_specialist_delegation(
            db=db,
            category=category,
            message=cleaned_message,
            customer_id=ticket.customer_id,
        )

        ai_msg: Optional[TicketMessage] = None
        action_taken = "ROUTED_WITHOUT_REPLY"

        if reply_content:
            ai_msg = TicketMessage(
                ticket_id=ticket.id,
                sender_id=None,
                sender_type="AI",
                content=reply_content,
            )
            db.add(ai_msg)
            action_taken = f"REPLIED_VIA_{category.value}"

        db.commit()
        db.refresh(user_msg)
        if ai_msg:
            db.refresh(ai_msg)

        return AIReplyResponse(
            message_content=reply_content,
            routing_decision=decision,
            action_taken=action_taken,
            user_message=TicketMessageResponse.model_validate(user_msg),
            ai_message=TicketMessageResponse.model_validate(ai_msg) if ai_msg else None,
        )
    except Exception:
        db.rollback()
        raise
