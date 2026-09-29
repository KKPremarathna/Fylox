from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TicketActivityResponse(BaseModel):
    id: int
    ticket_id: int
    actor_id: Optional[int]
    event_type: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)