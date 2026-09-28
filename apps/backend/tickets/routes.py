from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.tickets.models import Ticket
from backend.tickets.schemas import TicketCreate, TicketResponse

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"],
)

# Create ticket
@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    ticket: TicketCreate,
    db: Session = Depends(get_db),
):
    new_ticket = Ticket(
        customer_id=ticket.customer_id,
        subject=ticket.subject,
        description=ticket.description,
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket

# Get all tickets
@router.get("", response_model=list[TicketResponse])
def list_tickets(db: Session = Depends(get_db)):
    statement = select(Ticket).order_by(Ticket.created_at.desc())
    tickets = db.scalars(statement).all()

    return tickets

# Get a ticket ny ID
@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket