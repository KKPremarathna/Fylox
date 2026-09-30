from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.admin.routes import require_admin
from backend.approvals.models import ApprovalRequest
from backend.approvals.schemas import (
    ApprovalDecisionPatch,
    ApprovalPaginatedResponse,
    ApprovalRequestResponse,
    RefundReviewCreate,
)
from backend.approvals.service import (
    create_refund_review_request,
    process_approval_decision,
)
from backend.database import get_db
from backend.orders.service import get_order_for_owner_or_admin
from backend.security import get_current_user
from backend.tickets.service import get_ticket_for_owner_or_admin
from backend.users.models import User

# --- Customer / General Endpoints Rooted on Orders ---
customer_router = APIRouter(
    prefix="/orders/{order_id}/refund-review-requests",
    tags=["Approvals"],
)


@customer_router.post("", response_model=ApprovalRequestResponse, status_code=201)
def create_refund_request(
    order_id: int,
    payload: RefundReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    authorized_order = get_order_for_owner_or_admin(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )
    authorized_ticket = get_ticket_for_owner_or_admin(
        db=db,
        ticket_id=payload.ticket_id,
        current_user=current_user,
    )

    return create_refund_review_request(
        db=db,
        order=authorized_order,
        ticket=authorized_ticket,
        reason=payload.reason,
        current_user=current_user,
    )


@customer_router.get("", response_model=list[ApprovalRequestResponse])
def list_order_refund_requests(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    authorized_order = get_order_for_owner_or_admin(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )
    
    statement = (
        select(ApprovalRequest)
        .where(ApprovalRequest.order_id == authorized_order.id)
        .order_by(ApprovalRequest.created_at.desc())
    )
    return db.scalars(statement).all()


# --- Admin Endpoints Rooted Global Defaults ---
admin_router = APIRouter(
    prefix="/admin/approval-requests",
    tags=["Admin", "Approvals"],
    dependencies=[Depends(require_admin)],
)


@admin_router.get("", response_model=ApprovalPaginatedResponse)
def list_admin_approval_requests(
    status: Optional[str] = Query(None, description="Filter by generic status state"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status is not None:
        statement = statement.where(ApprovalRequest.status == status)
        
    # Standard manual counting mapping natively to pagination blocks
    # Using python scaling initially per legacy configuration patterns
    all_requests = db.scalars(statement).all()
    total = len(all_requests)
    
    # Safe limits applied against in-memory slices
    paged = all_requests[offset : offset + limit]
    
    return {
        "items": paged,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@admin_router.patch("/{request_id}", response_model=ApprovalRequestResponse)
def evaluate_approval_request(
    request_id: int,
    payload: ApprovalDecisionPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return process_approval_decision(
        db=db,
        request_id=request_id,
        patch=payload,
        current_user=current_user,
    )
