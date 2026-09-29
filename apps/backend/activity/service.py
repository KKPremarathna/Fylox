from typing import Optional

from sqlalchemy.orm import Session

from backend.activity.models import TicketActivity


def record_activity(
    db: Session,
    ticket_id: int,
    actor_id: Optional[int],
    event_type: str,
    message: str,
) -> TicketActivity:
    activity = TicketActivity(
        ticket_id=ticket_id,
        actor_id=actor_id,
        event_type=event_type,
        message=message,
    )

    db.add(activity)

    return activity