from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.ai.schemas import AIReplyResponse, ClassifyRequest
from backend.ai.service import execute_triage, process_ticket_ai_reply
from backend.database import get_db
from backend.tickets.service import get_ticket_for_owner_or_admin
from backend.security import get_current_user
from backend.users.models import User


router = APIRouter(
    prefix="/ai",
    tags=["AI Router"]
)


@router.post("/classify", response_model=AIReplyResponse)
def classify_message_endpoint(payload: ClassifyRequest):
    """
    Public simulation path to explicitly evaluate message classification without DB writes.
    """
    return execute_triage(payload)


# Mounted explicitly overlapping Ticket domains natively utilizing established security middleware bounds
@router.post("/tickets/{ticket_id}/ai-reply", response_model=AIReplyResponse)
def generate_ticket_ai_reply(
    ticket_id: int, 
    payload: ClassifyRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes standard ticket retrieval security verification bounds and then hooks into 
    the strict agent boundaries.
    """
    authorized_ticket = get_ticket_for_owner_or_admin(db, ticket_id, current_user)
    if not authorized_ticket:
         raise HTTPException(status_code=404, detail="Ticket not found")

    return process_ticket_ai_reply(db=db, ticket=authorized_ticket, message=payload.message)
