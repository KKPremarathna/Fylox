from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.messages.models import TicketMessage
from backend.messages.schemas import (
    TicketMessageCreate,
    TicketMessageResponse,
)
from backend.security import get_current_user
from backend.tickets.models import Ticket
from backend.users.models import User

router = APIRouter(
    prefix="/tickets",
    tags=["Ticket Messages"],
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


@router.post(
    "/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket_message(
    ticket_id: int,
    message: TicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_ticket(
        ticket_id=ticket_id,
        db=db,
        current_user=current_user,
    )

    sender_type = (
        "ADMIN"
        if current_user.role == "ADMIN"
        else "CUSTOMER"
    )

    new_message = TicketMessage(
        ticket_id=ticket_id,
        sender_id=current_user.user_id,
        sender_type=sender_type,
        content=message.content,
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


@router.get(
    "/{ticket_id}/messages",
    response_model=list[TicketMessageResponse],
)
def list_ticket_messages(
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
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc())
    )

    messages = db.scalars(statement).all()

    return messages