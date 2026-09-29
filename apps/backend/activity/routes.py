from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.activity.models import TicketActivity
from backend.activity.schemas import TicketActivityResponse
from backend.database import get_db
from backend.security import get_current_user
from backend.tickets.models import Ticket
from backend.users.models import User


router = APIRouter(
    prefix="/tickets",
    tags=["Ticket Activity"],
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
        .order_by(TicketActivity.created_at.asc())
    )

    return db.scalars(statement).all()