from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.security import get_current_user
from backend.tickets.models import Ticket
from backend.ml.service import suggest_ticket_category
from backend.tickets.schemas import (
    TicketCategoryReview,
    TicketCategorySuggestionResponse,
    TicketCreate,
    TicketResponse,
)
from backend.users.models import User
from backend.activity.service import record_activity

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"],
)


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    ticket: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_ticket = Ticket(
        customer_id=current_user.user_id,
        subject=ticket.subject,
        description=ticket.description,
    )

    db.add(new_ticket)

    # Sends the ticket insert to PostgreSQL so new_ticket.id is available,
    # but does not permanently save the transaction yet.
    db.flush()

    record_activity(
        db=db,
        ticket_id=new_ticket.id,
        actor_id=current_user.user_id,
        event_type="TICKET_CREATED",
        message="Ticket created.",
    )

    # One commit saves both the ticket and its first activity record.
    db.commit()

    db.refresh(new_ticket)

    return new_ticket


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Ticket).order_by(Ticket.created_at.desc())

    if current_user.role == "CUSTOMER":
        statement = statement.where(
            Ticket.customer_id == current_user.user_id
        )

    tickets = db.scalars(statement).all()

    return tickets

@router.post(
    "/{ticket_id}/ai/category-suggestion",
    response_model=TicketCategorySuggestionResponse,
)
def create_category_suggestion(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can request AI category suggestions.",
        )

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    suggestion = suggest_ticket_category(
        subject=ticket.subject,
        description=ticket.description,
    )

    ticket.ai_suggested_category = suggestion["suggested_category"]
    ticket.ai_category_confidence = suggestion["confidence"]

    db.commit()
    db.refresh(ticket)

    return {
        "ticket_id": ticket.id,
        "suggested_category": ticket.ai_suggested_category,
        "confidence": ticket.ai_category_confidence,
    }

@router.patch(
    "/{ticket_id}/accept-ai-category",
    response_model=TicketResponse,
)
def accept_ai_category(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can accept AI category suggestions.",
        )

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if ticket.ai_suggested_category is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request an AI category suggestion before accepting it.",
        )

    ticket.final_category = ticket.ai_suggested_category
    ticket.ai_category_approved = True

    record_activity(
        db=db,
        ticket_id=ticket.id,
        actor_id=current_user.user_id,
        event_type="AI_CATEGORY_ACCEPTED",
        message=(
            f"Admin accepted AI category suggestion: "
            f"{ticket.ai_suggested_category}."
        ),
    )

    db.commit()
    db.refresh(ticket)

    return ticket

@router.patch(
    "/{ticket_id}/category-review",
    response_model=TicketResponse,
)
def review_ticket_category(
    ticket_id: int,
    review: TicketCategoryReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can review ticket categories.",
        )

    ticket = db.get(Ticket, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    ticket.final_category = review.final_category

    if ticket.ai_suggested_category is None:
        ticket.ai_category_approved = None
        activity_message = (
            f"Admin manually set category: {review.final_category}."
        )
        event_type = "CATEGORY_MANUALLY_SET"
    else:
        ticket.ai_category_approved = (
            review.final_category == ticket.ai_suggested_category
        )
        activity_message = (
            f"Admin reviewed category: {review.final_category}. "
            f"AI suggestion was {ticket.ai_suggested_category}."
        )
        event_type = "AI_CATEGORY_REVIEWED"

    record_activity(
        db=db,
        ticket_id=ticket.id,
        actor_id=current_user.user_id,
        event_type=event_type,
        message=activity_message,
    )

    db.commit()
    db.refresh(ticket)

    return ticket

@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

