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


class AdminActivityItem(BaseModel):
    id: int
    ticket_id: int
    ticket_subject: str
    actor_id: Optional[int]
    actor_username: Optional[str]
    event_type: str
    message: str
    created_at: datetime


class AdminActivityHistoryResponse(BaseModel):
    items: list[AdminActivityItem]
    total: int
    limit: int
    offset: int