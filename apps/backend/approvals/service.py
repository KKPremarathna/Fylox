from datetime import datetime, timezone
import json

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.activity.models import TicketActivity
from backend.approvals.models import ApprovalRequest
from backend.approvals.schemas import ApprovalDecisionPatch, ApprovalStatus
from backend.orders.models import Order
from backend.payments.models import Payment
from backend.payments.service import check_duplicate_charges
from backend.tickets.models import Ticket
from backend.users.models import User


def create_refund_review_request(
    db: Session,
    order: Order,
    ticket: Ticket,
    reason: str,
    current_user: User,
) -> ApprovalRequest:
    """
    Creates a new PENDING approval request for a REFUND_REVIEW and securely stores
    only necessary safe aggregate data as evidence, along with the ticket activity string.
    """
    # Defensive cross-check explicitly maintaining data parity
    if current_user.role == "CUSTOMER":
        if ticket.customer_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ticket does not belong to the user",
            )
        if order.customer_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Order does not belong to the user",
            )
        if ticket.customer_id != order.customer_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order and Ticket owner mismatch",
            )

    # Calculate duplicate statistics cleanly on the server to prevent untrusted payload manipulation
    payments = db.scalars(select(Payment).where(Payment.order_id == order.id)).all()
    check_report = check_duplicate_charges(order_id=order.id, payments=payments)

    if not check_report.has_possible_duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order not eligible for duplicate refund review currently",
        )

    evidence = {
        "rule_engine": "v1_basic_exact_match",
        "successful_payment_count": check_report.successful_payment_count,
        "duplicate_groups": [
            g.model_dump(mode="json") for g in check_report.duplicate_groups
        ],
    }
    
    # Intentionally strip ALL private info. Evidence is purely statistical JSON dict.
    
    approval_request = ApprovalRequest(
        ticket_id=ticket.id,
        order_id=order.id,
        request_type="REFUND_REVIEW",
        status="PENDING",
        requested_by_user_id=current_user.user_id,
        reason=reason,
        evidence_json=evidence,
    )
    
    db.add(approval_request)
    
    # Safely commit evaluating Index barrier for pre-existing pending constraints
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active pending request already exists for this order.",
        )
        
    activity = TicketActivity(
        ticket_id=ticket.id,
        actor_id=current_user.user_id,
        event_type="REFUND_REVIEW_REQUESTED",
        message=f"Refund review requested for Order #{order.order_number}"
    )
    db.add(activity)
    
    db.commit()
    db.refresh(approval_request)
    
    return approval_request


def process_approval_decision(
    db: Session,
    request_id: int,
    patch: ApprovalDecisionPatch,
    current_user: User,
) -> ApprovalRequest:
    """
    Opportunistically completes a PENDING approval requirement safely, logging output back into TicketActivity.
    """
    if patch.status == ApprovalStatus.REJECTED:
        if not patch.reviewer_note or not patch.reviewer_note.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A reviewer note is strictly required for rejection",
            )
            
    now = datetime.now(timezone.utc)
    
    result = db.execute(
        update(ApprovalRequest)
        .where(
            ApprovalRequest.id == request_id, 
            ApprovalRequest.status == "PENDING"
        )
        .values(
            status=patch.status,
            reviewed_by_user_id=current_user.user_id,
            reviewed_at=now,
            reviewer_note=patch.reviewer_note,
            updated_at=now
        )
    )
    
    if result.rowcount == 0:
        # Evaluate context behind the 0-update scenario natively
        existing = db.get(ApprovalRequest, request_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval request has already been decided or cancelled",
            )
    
    approval_request = db.get(ApprovalRequest, request_id)
    
    # Audit trail linking directly back into standard ticketing history hooks synchronously
    event_type = "REFUND_REVIEW_APPROVED" if patch.status == ApprovalStatus.APPROVED else "REFUND_REVIEW_REJECTED"
    
    activity = TicketActivity(
        ticket_id=approval_request.ticket_id,
        actor_id=current_user.user_id,
        event_type=event_type,
        message=f"Refund review {patch.status.value.lower()}. Note: {patch.reviewer_note or 'None'}"
    )
    db.add(activity)
    db.commit()
    db.refresh(approval_request)
    
    return approval_request
