from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.admin.schemas import AdminTicketUpdate
from backend.database import get_db
from backend.security import get_current_user
from backend.tickets.models import Ticket
from backend.tickets.schemas import TicketResponse
from backend.users.models import User
from backend.activity.service import record_activity


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
        admin_id = changes["assigned_admin_id"]
        old_admin_id = ticket.assigned_admin_id

        if admin_id is None:
            ticket.assigned_admin_id = None

            if old_admin_id is not None:
                record_activity(
                    db=db,
                    ticket_id=ticket.id,
                    actor_id=current_user.user_id,
                    event_type="TICKET_UNASSIGNED",
                    message="Ticket was unassigned.",
                )

        else:
            admin = (
                db.query(User)
                .filter(
                    User.user_id == admin_id,
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

            if old_admin_id != admin.user_id:
                record_activity(
                    db=db,
                    ticket_id=ticket.id,
                    actor_id=current_user.user_id,
                    event_type="TICKET_ASSIGNED",
                    message=f"Ticket assigned to admin ID {admin.user_id}.",
                )

    if "status" in changes:
        old_status = ticket.status
        new_status = changes["status"].value

        ticket.status = new_status

        if old_status != new_status:
            event_type = "STATUS_CHANGED"

            if new_status == "RESOLVED":
                event_type = "TICKET_RESOLVED"
            elif new_status == "CLOSED":
                event_type = "TICKET_CLOSED"

            record_activity(
                db=db,
                ticket_id=ticket.id,
                actor_id=current_user.user_id,
                event_type=event_type,
                message=(
                    f"Ticket status changed from "
                    f"{old_status} to {new_status}."
                ),
            )

    db.commit()
    db.refresh(ticket)

    return ticket