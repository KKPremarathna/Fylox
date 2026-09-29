from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class AdminTicketUpdate(BaseModel):
    assigned_admin_id: Optional[int] = Field(
        default=None,
        description="User ID of the admin assigned to the ticket",
    )
    status: Optional[TicketStatus] = None