from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.tickets.models import Ticket
from backend.users.models import User


def get_ticket_for_owner_or_admin(
    db: Session,
    ticket_id: int,
    current_user: User,
) -> Ticket:
    """
    Centralized authorization helper for ticket access.
    
    Returns the ticket if the user is an ADMIN or the customer who owns the ticket.
    Raises 404 if the ticket does not exist.
    Raises 403 if the user is a non-owning customer.
    """
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
