from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TicketMessageCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=5000,
        examples=[
            "I was charged twice. Please help me check the payment."
        ],
    )


class TicketMessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    sender_type: Literal["CUSTOMER", "ADMIN", "AI"]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)