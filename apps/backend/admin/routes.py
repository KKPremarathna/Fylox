from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.admin.schemas import AdminTicketUpdate
from backend.tickets.models import Ticket
from backend.tickets.schemas import TicketResponse
from backend.users.models import User


router = APIRouter(
    prefix="/admin/tickets",
    tags=["Admin Tickets"],
)


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("", response_model=list[TicketResponse])
def list_all_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return (
        db.query(Ticket)
        .order_by(Ticket.created_at.desc())
        .all()
    )


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    payload: AdminTicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    if "assigned_admin_id" in changes:
        admin = (
            db.query(User)
            .filter(
                User.user_id == changes["assigned_admin_id"],
                User.role == "ADMIN",
            )
            .first()
        )

        if admin is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found",
            )

        ticket.assigned_admin_id = admin.user_id

    if "status" in changes:
        ticket.status = changes["status"].value

    db.commit()
    db.refresh(ticket)

    return ticket