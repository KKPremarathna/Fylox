from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.activity.models import TicketActivity
from backend.activity.schemas import (
    AdminActivityHistoryResponse,
    AdminActivityItem,
    TicketActivityResponse,
)
from backend.admin.routes import require_admin
from backend.database import get_db
from backend.security import get_current_user
from backend.tickets.models import Ticket
from backend.users.models import User


router = APIRouter(
    prefix="/tickets",
    tags=["Ticket Activity"],
)

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin Activity History"],
)


def get_accessible_ticket(
    ticket_id: int,
    db: Session,
    current_user: User,
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    is_owner = ticket.customer_id == current_user.user_id
    is_admin = current_user.role == "ADMIN"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this ticket",
        )

    return ticket


@router.get(
    "/{ticket_id}/activity",
    response_model=list[TicketActivityResponse],
)
def list_ticket_activity(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_ticket(
        ticket_id=ticket_id,
        db=db,
        current_user=current_user,
    )

    statement = (
        select(TicketActivity)
        .where(TicketActivity.ticket_id == ticket_id)
        .order_by(
            TicketActivity.created_at.asc(),
            TicketActivity.id.asc(),
        )
    )

    return db.scalars(statement).all()


@admin_router.get(
    "/activity",
    response_model=AdminActivityHistoryResponse,
)
def list_admin_activity(
    ticket_id: Optional[int] = Query(default=None, ge=1),
    event_type: Optional[str] = Query(default=None, max_length=100),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must not be after end_date.",
        )

    # Build the base join: TicketActivity -> Ticket (inner), -> User (outer)
    base = (
        select(
            TicketActivity.id,
            TicketActivity.ticket_id,
            Ticket.subject.label("ticket_subject"),
            TicketActivity.actor_id,
            User.username.label("actor_username"),
            TicketActivity.event_type,
            TicketActivity.message,
            TicketActivity.created_at,
        )
        .join(Ticket, TicketActivity.ticket_id == Ticket.id)
        .outerjoin(User, TicketActivity.actor_id == User.user_id)
    )

    # Apply optional filters
    if ticket_id is not None:
        base = base.where(TicketActivity.ticket_id == ticket_id)
    if event_type is not None:
        base = base.where(TicketActivity.event_type == event_type)
    if start_date is not None:
        base = base.where(TicketActivity.created_at >= start_date)
    if end_date is not None:
        base = base.where(TicketActivity.created_at <= end_date)

    # Count total matching rows (same filters, no pagination)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.scalar(count_stmt)

    # Fetch the paginated page
    paged = (
        base
        .order_by(
            TicketActivity.created_at.desc(),
            TicketActivity.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(paged).all()

    items = [
        AdminActivityItem(
            id=row.id,
            ticket_id=row.ticket_id,
            ticket_subject=row.ticket_subject,
            actor_id=row.actor_id,
            actor_username=row.actor_username,
            event_type=row.event_type,
            message=row.message,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return AdminActivityHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )